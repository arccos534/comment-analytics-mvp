from __future__ import annotations

import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.analytics.aggregator import ReportAggregator
from app.analytics.llm_comment_analyzer import LLMCommentAnalyzer
from app.analytics.prompt_intent import (
    GENERIC_PROMPT_SCOPE_TERMS as SHARED_GENERIC_PROMPT_SCOPE_TERMS,
    apply_analysis_mode_override as apply_shared_analysis_mode_override,
    build_prompt_intent as build_shared_prompt_intent,
    extract_prompt_scope_terms as extract_shared_prompt_scope_terms,
)
from app.analytics.prompt_router import PromptRouter
from app.analytics.relevance import RelevanceScorer
from app.analytics.sentiment import SentimentAnalyzer
from app.core.config import get_settings
from app.models.analysis_run import AnalysisRun
from app.models.enums import AnalysisRunStatusEnum, SentimentEnum
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.analytics import AnalysisCreateRequest
from app.services.report_service import ReportService
from app.utils.dates import utcnow

logger = logging.getLogger(__name__)

REPORT_TITLE_STOPWORDS = {
    "проанализируй",
    "проанализировать",
    "анализ",
    "какие",
    "какой",
    "какая",
    "какие",
    "какое",
    "каким",
    "каких",
    "нужно",
    "надо",
    "хочу",
    "покажи",
    "показать",
    "найди",
    "найти",
    "оцени",
    "оценить",
    "сделай",
    "сделать",
    "дай",
    "дать",
    "реакцию",
    "реакции",
    "отношение",
    "аудитории",
    "людей",
    "комментарии",
    "комментариев",
    "комментариям",
    "комментария",
    "новости",
    "новостей",
    "новостям",
    "посты",
    "постов",
    "постам",
    "отчет",
    "отчёт",
    "отчета",
    "отчёта",
    "отчеты",
    "отчёты",
    "теме",
    "тему",
    "вопросу",
    "вопрос",
}

PROMPT_SCOPE_STOPWORDS = {
    "проанализируй",
    "проанализировать",
    "анализ",
    "какой",
    "какая",
    "какие",
    "какого",
    "каких",
    "какому",
    "каким",
    "покажи",
    "показать",
    "найди",
    "найти",
    "оцени",
    "оценить",
    "сделай",
    "сделать",
    "дай",
    "дать",
    "нужно",
    "надо",
    "хочу",
    "ответ",
    "ответь",
    "вывод",
    "новость",
    "новости",
    "пост",
    "посты",
    "люди",
    "думают",
    "думать",
    "мнение",
    "реакция",
    "реакции",
    "реакцию",
    "аудитории",
    "людей",
    "комментарии",
    "комментариев",
    "комментариям",
    "комментария",
    "интерес",
    "интересные",
    "интересное",
    "вызывает",
    "вызывают",
    "вызвали",
    "вызвала",
    "негатив",
    "негативные",
    "позитив",
    "позитивные",
    "эмоции",
    "эмоцию",
    "самой",
    "самая",
    "самый",
    "обсуждаемая",
    "обсуждаемой",
    "обсуждаемую",
    "обсуждаемый",
    "обсуждали",
}

GENERIC_THEME_SCOPE_TERMS = {
    "город",
    "города",
    "городе",
    "новость",
    "новости",
    "пост",
    "посты",
    "тема",
    "темы",
}

RUSSIAN_STEM_SUFFIXES = (
    "иями",
    "ями",
    "ами",
    "иях",
    "ого",
    "ему",
    "ому",
    "ыми",
    "ими",
    "иям",
    "ием",
    "ов",
    "ев",
    "ей",
    "ой",
    "ий",
    "ый",
    "ая",
    "ое",
    "ые",
    "ых",
    "ую",
    "юю",
    "ом",
    "ем",
    "ам",
    "ям",
    "ах",
    "ях",
    "ию",
    "ья",
    "ия",
    "а",
    "я",
    "ы",
    "и",
    "е",
    "у",
    "ю",
    "о",
)


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.comments = CommentRepository(db)
        self.posts = PostRepository(db)
        self.analysis_repo = AnalysisRepository(db)
        self.comment_llm = LLMCommentAnalyzer()
        self.prompt_router = PromptRouter()
        self.sentiment = SentimentAnalyzer()
        self.relevance = RelevanceScorer()
        self.aggregator = ReportAggregator()
        self.report_service = ReportService()

    def project_exists(self, project_id: UUID) -> bool:
        return self.projects.exists(project_id)

    def create_and_enqueue_run(self, project_id: UUID, payload: AnalysisCreateRequest):
        run = AnalysisRun(
            project_id=project_id,
            prompt_text=payload.prompt_text,
            theme=payload.theme,
            keywords_json=payload.keywords,
            period_from=payload.period_from,
            period_to=payload.period_to,
            filters_json={
                "platforms": [platform.value for platform in payload.platforms],
                "source_ids": [str(source_id) for source_id in payload.source_ids],
                "analysis_mode_override": (payload.analysis_mode_override or "").strip() or None,
            },
            status=AnalysisRunStatusEnum.pending,
        )
        run = self.analysis_repo.create_run(run)
        settings = get_settings()
        if settings.demo_mode or not settings.background_jobs_enabled:
            self.execute_run_sync(run.id)
            refreshed = self.analysis_repo.get_run(run.id)
            return refreshed or run
        try:
            from app.tasks.analytics_tasks import run_analysis_task

            run_analysis_task.delay(str(run.id))
        except Exception:
            self.execute_run_sync(run.id)
        return run

    def get_run(self, analysis_run_id: UUID):
        return self.analysis_repo.get_run(analysis_run_id)

    def get_report(self, analysis_run_id: UUID):
        return self.analysis_repo.get_report(analysis_run_id)

    def delete_report(self, analysis_run_id: UUID) -> bool:
        return self.analysis_repo.delete_run(analysis_run_id)

    def list_reports_tree(self) -> list[dict]:
        grouped: dict[UUID, dict] = {}
        for project, run, _snapshot in self.analysis_repo.list_reports_tree():
            bucket = grouped.setdefault(
                project.id,
                {
                    "project_id": project.id,
                    "project_name": project.name,
                    "reports": [],
                },
            )
            bucket["reports"].append(
                {
                    "analysis_run_id": run.id,
                    "title": self._build_report_title(run.theme, run.prompt_text),
                    "created_at": run.created_at,
                }
            )
        return list(grouped.values())

    def _build_report_title(self, theme: str | None, prompt_text: str) -> str:
        if (theme or "").strip():
            return self._format_report_title(theme or "")

        derived = self._derive_title_from_prompt(prompt_text)
        return self._format_report_title(derived or prompt_text)

    def _format_report_title(self, value: str) -> str:
        normalized = re.sub(r"\s+", " ", value).strip(" ,.;:-")
        words = normalized.split()
        shortened = " ".join(words[:4]) if words else normalized
        if not shortened:
            return "Report"
        return shortened[:1].upper() + shortened[1:]

    def _derive_title_from_prompt(self, prompt_text: str) -> str:
        prompt = re.sub(r"\s+", " ", prompt_text).strip()

        phrase_patterns = [
            r"\b(?:по|про|о|об|относительно|насчет)\s+([A-Za-zА-Яа-яЁё0-9-]+(?:\s+[A-Za-zА-Яа-яЁё0-9-]+){0,4})",
            r"\bк\s+([A-Za-zА-Яа-яЁё0-9-]+(?:\s+[A-Za-zА-Яа-яЁё0-9-]+){0,4})",
        ]
        for pattern in phrase_patterns:
            match = re.search(pattern, prompt, flags=re.IGNORECASE)
            if not match:
                continue
            cleaned = self._strip_generic_title_words(match.group(1))
            if cleaned:
                return cleaned

        tokens = re.findall(r"[A-Za-zА-Яа-яЁё0-9-]{3,}", prompt.lower())
        meaningful = [token for token in tokens if token not in REPORT_TITLE_STOPWORDS]
        if meaningful:
            return " ".join(meaningful[-3:])
        return prompt

    def _strip_generic_title_words(self, phrase: str) -> str:
        words = [word for word in re.findall(r"[A-Za-zА-Яа-яЁё0-9-]+", phrase) if word]
        while words and words[0].lower() in REPORT_TITLE_STOPWORDS:
            words.pop(0)
        return " ".join(words[:4])

    def _tokenize_scope(self, value: str) -> set[str]:
        return set(re.findall(r"[A-Za-zА-Яа-яЁё0-9-]{4,}", value.lower()))

    def _normalize_term(self, value: str) -> str:
        return " ".join((value or "").lower().replace("ё", "е").split())

    def _stem_token(self, token: str) -> str:
        normalized = self._normalize_term(token)
        for suffix in RUSSIAN_STEM_SUFFIXES:
            if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 4:
                return normalized[: -len(suffix)]
        return normalized

    def _extract_text_roots(self, text: str) -> set[str]:
        tokens = re.findall(r"[a-zа-я0-9-]{4,}", self._normalize_term(text))
        roots = {self._stem_token(token) for token in tokens}
        return {root for root in roots if root}

    def _term_matches_scope(self, term: str, normalized_text: str, text_roots: set[str]) -> bool:
        normalized_term = self._normalize_term(term)
        if normalized_term and normalized_term in normalized_text:
            return True

        root = self._stem_token(normalized_term)
        if not root:
            return False

        for candidate in text_roots:
            if candidate == root:
                return True
            if len(root) >= 5 and (candidate.startswith(root) or root.startswith(candidate)):
                return True
        return False

    def _extract_theme_scope_terms(self, theme: str | None, keywords: list[str] | None) -> list[str]:
        values = " ".join([(theme or "").strip(), " ".join(keywords or [])])
        tokens = re.findall(r"[a-zа-я0-9-]{4,}", self._normalize_term(values))
        ordered: list[str] = []
        for token in tokens:
            if token in PROMPT_SCOPE_STOPWORDS or token in GENERIC_THEME_SCOPE_TERMS:
                continue
            if token not in ordered:
                ordered.append(token)
        return ordered[:8]

    def _extract_prompt_scope_terms(self, prompt_text: str | None) -> list[str]:
        return extract_shared_prompt_scope_terms(prompt_text)

    def _matches_prompt_scope(self, post_text: str | None, prompt_text: str | None) -> bool:
        text = (post_text or "").strip()
        if not text:
            return False

        prompt_intent = build_shared_prompt_intent(prompt_text, has_explicit_scope=False)
        if prompt_intent.generic_scope:
            return True

        focus_terms = prompt_intent.focus_terms
        if not focus_terms:
            return True

        lowered = self._normalize_term(text)
        roots = self._extract_text_roots(lowered)
        overlap = sum(1 for token in focus_terms if self._term_matches_scope(token, lowered, roots))
        if overlap >= 2 or (len(focus_terms) <= 3 and overlap >= 1):
            return True

        return self.relevance.score(text, (prompt_text or "").strip()) >= 0.15

    def _is_advertising_post(self, post_text: str | None) -> bool:
        text = (post_text or "").strip().lower()
        if not text:
            return False

        ad_markers = {
            "реклама",
            "erid",
            "рекламодатель",
            "партнерский материал",
            "при поддержке",
            "спонсор",
            "скидка",
            "промокод",
            "акция",
            "купить",
            "заказать",
            "оформить заказ",
            "записывайтесь",
            "самовывоз",
            "доставка по",
            "подробности по ссылке",
        }
        if any(marker in text for marker in ad_markers):
            return True

        links_count = len(re.findall(r"https?://|www\.", text))
        phone_count = len(re.findall(r"(?:\+7|8)[\s()\-]*\d", text))
        cta_markers = sum(
            1
            for marker in {"по ссылке", "звоните", "подробнее", "стоимость", "цены", "в наличии", "вопросы по телефону"}
            if marker in text
        )
        return links_count >= 2 or phone_count >= 1 or (links_count >= 1 and cta_markers >= 1)

    def _matches_post_scope(
        self,
        post_text: str | None,
        theme: str | None,
        keywords: list[str] | None,
        prompt_text: str | None = None,
    ) -> bool:
        keywords = keywords or []
        has_post_scope = bool((theme or "").strip() or keywords)
        if not has_post_scope:
            return self._matches_prompt_scope(post_text, prompt_text)

        text = (post_text or "").strip()
        if not text:
            return False

        lowered = text.lower()
        normalized_keywords = [keyword.strip().lower() for keyword in keywords if keyword.strip()]
        if normalized_keywords and any(keyword in lowered for keyword in normalized_keywords):
            return True

        theme_terms = self._extract_theme_scope_terms(theme, normalized_keywords)
        post_roots = self._extract_text_roots(lowered)
        if theme_terms:
            term_overlap = sum(1 for token in theme_terms if self._term_matches_scope(token, lowered, post_roots))
            if term_overlap >= 1:
                return True

        scope_tokens = self._tokenize_scope(" ".join([theme or "", " ".join(normalized_keywords)]))
        post_tokens = self._tokenize_scope(text)
        token_overlap = len(scope_tokens & post_tokens)
        if token_overlap >= 2:
            return True

        topic_score = self.relevance.score_post_topic(text=text, theme=theme, keywords=keywords)
        if normalized_keywords:
            return topic_score >= 0.22
        if theme_terms:
            return topic_score >= 0.32
        return topic_score >= 0.18

    def _is_source_metric_prompt(self, prompt_text: str | None) -> bool:
        return build_shared_prompt_intent(prompt_text, has_explicit_scope=False).source_only

    def execute_run_sync(self, analysis_run_id: UUID) -> dict:
        run = self.analysis_repo.update_run_status(analysis_run_id, AnalysisRunStatusEnum.running)
        if not run:
            return {"status": "not_found"}
        try:
            platform_filters = (run.filters_json or {}).get("platforms") or []
            source_filters = [UUID(value) for value in ((run.filters_json or {}).get("source_ids") or [])]
            available_sources = self._resolve_analysis_sources(run.project_id, source_filters, platform_filters)
            post_records = self.posts.get_analysis_posts(
                run.project_id,
                period_from=run.period_from,
                period_to=run.period_to,
                source_ids=source_filters,
                platforms=platform_filters,
            )
            has_explicit_scope = bool((run.theme or "").strip() or (run.keywords_json or []))
            prompt_route = self.prompt_router.route(
                run.prompt_text,
                has_explicit_scope=has_explicit_scope,
                override_mode=(run.filters_json or {}).get("analysis_mode_override"),
            )
            prompt_intent = prompt_route.intent
            source_only_prompt = prompt_intent.source_only
            records = (
                self.comments.get_analysis_records(
                    run.project_id,
                    period_from=run.period_from,
                    period_to=run.period_to,
                    source_ids=source_filters,
                    platforms=platform_filters,
                )
                if prompt_route.needs_comment_analysis
                else []
            )
            if source_only_prompt:
                scoped_posts = [
                    {"post": post, "source": source}
                    for post, source in post_records
                    if not self._is_advertising_post(post.post_text)
                ]
            else:
                scoped_posts = [
                    {"post": post, "source": source}
                    for post, source in post_records
                    if self._matches_post_scope(
                        post.post_text,
                        run.theme,
                        run.keywords_json or [],
                        run.prompt_text,
                    )
                    and not self._is_advertising_post(post.post_text)
                ]

            scoped_post_ids = {record["post"].id for record in scoped_posts}
            scoped_records = [
                record
                for record in records
                if record[1].id in scoped_post_ids and not self._is_advertising_post(record[1].post_text)
            ]

            enriched_comments: list[dict] = []
            if prompt_route.needs_comment_analysis:
                comment_analysis_inputs: list[dict] = []
                for comment, post, source in scoped_records:
                    relevance_score = self.relevance.score_comment_prompt(
                        text=comment.text,
                        prompt_text=run.prompt_text,
                    )
                    if post.id in scoped_post_ids and not source_only_prompt:
                        relevance_score = max(relevance_score, 0.2)
                    comment_analysis_inputs.append(
                        {
                            "comment": comment,
                            "post": post,
                            "source": source,
                            "comment_text": comment.text,
                            "post_text": post.post_text or "",
                            "relevance_score": relevance_score,
                        }
                    )

                llm_comment_results = self.comment_llm.analyze_many(
                    [
                        {
                            "comment_text": item["comment_text"],
                            "post_text": item["post_text"],
                        }
                        for item in comment_analysis_inputs
                    ]
                )

                for item, analysis in zip(comment_analysis_inputs, llm_comment_results):
                    comment = item["comment"]
                    post = item["post"]
                    source = item["source"]
                    relevance_score = item["relevance_score"]
                    sentiment_value = analysis["sentiment"]
                    try:
                        sentiment_enum = SentimentEnum(sentiment_value)
                    except ValueError:
                        sentiment_enum = self.sentiment.analyze(comment.text)["sentiment"]
                        sentiment_value = sentiment_enum.value
                    topics = analysis["topics"]
                    extracted_keywords = analysis["keywords"]
                    self.analysis_repo.upsert_comment_analysis(
                        comment_id=comment.id,
                        sentiment=sentiment_enum,
                        sentiment_score=analysis["score"],
                        topics_json=topics,
                        keywords_json=extracted_keywords,
                        relevance_score=relevance_score,
                        commit=False,
                    )
                    enriched_comments.append(
                        {
                            "comment": comment,
                            "post": post,
                            "source": source,
                            "sentiment": sentiment_value,
                            "sentiment_score": analysis["score"],
                            "topics": topics,
                            "keywords": extracted_keywords,
                            "relevance_score": relevance_score,
                        }
                    )

                self.db.commit()

            report_json = self.aggregator.build_report(
                run=run,
                enriched_comments=enriched_comments,
                filters={
                    "platforms": platform_filters,
                    "source_ids": [str(source_id) for source_id in source_filters],
                },
                scoped_posts=scoped_posts,
                selected_sources=available_sources,
            )
            report_json.setdefault("meta", {}).update(
                {
                    "router_source": prompt_route.router_source,
                    "router_confidence": prompt_route.confidence,
                    "router_reason": prompt_route.reason,
                    "needs_llm_reasoning": prompt_route.needs_llm_reasoning,
                    "needs_comment_analysis": prompt_route.needs_comment_analysis,
                    "needs_theme_analysis": prompt_route.needs_theme_analysis,
                }
            )
            summary_data, summary_text = self.report_service.build_summary(
                report_json,
                prompt_text=run.prompt_text,
                prompt_route={
                    "analysis_mode": prompt_route.analysis_mode,
                    "needs_llm_reasoning": prompt_route.needs_llm_reasoning,
                    "needs_comment_analysis": prompt_route.needs_comment_analysis,
                    "needs_theme_analysis": prompt_route.needs_theme_analysis,
                    "confidence": prompt_route.confidence,
                    "router_source": prompt_route.router_source,
                    "reason": prompt_route.reason,
                    "primary_mode": prompt_intent.primary_mode,
                    "prompt_modes": prompt_intent.prompt_mode,
                    "secondary_modes": prompt_intent.secondary_modes,
                    "analysis_axes": prompt_intent.analysis_axes,
                    "request_contract": prompt_intent.request_contract,
                    "answer_strategy": prompt_intent.answer_strategy,
                },
            )
            report_json["summary"] = summary_data
            self.analysis_repo.replace_report_snapshot(run.id, report_json, summary_text)
            self.analysis_repo.update_run_status(run.id, AnalysisRunStatusEnum.completed, finished_at=utcnow())
            return {"status": "completed", "analysis_run_id": str(run.id)}
        except Exception:
            logger.exception("Analytics run failed", extra={"analysis_run_id": str(run.id), "project_id": str(run.project_id)})
            self.analysis_repo.update_run_status(run.id, AnalysisRunStatusEnum.failed, finished_at=utcnow())
            return {"status": "failed", "analysis_run_id": str(run.id)}

    def _resolve_analysis_sources(self, project_id: UUID, source_filters: list[UUID], platform_filters: list[str]) -> list[dict]:
        project = self.projects.get(project_id)
        sources = project.sources if project else []
        resolved: list[dict] = []
        for source in sources:
            if source_filters and source.id not in source_filters:
                continue
            platform = getattr(source.platform, "value", str(source.platform))
            if platform_filters and platform not in platform_filters:
                continue
            resolved.append(
                {
                    "source_id": str(source.id),
                    "source_title": source.title,
                    "source_url": source.source_url,
                    "platform": platform,
                    "subscriber_count": source.subscriber_count,
                }
            )
        return resolved
