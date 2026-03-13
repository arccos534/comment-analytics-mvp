from __future__ import annotations

import logging
import re
from uuid import UUID

from sqlalchemy.orm import Session

from app.analytics.aggregator import ReportAggregator
from app.analytics.keywords import KeywordExtractor
from app.analytics.relevance import RelevanceScorer
from app.analytics.sentiment import SentimentAnalyzer
from app.analytics.topics import TopicGrouper
from app.core.config import get_settings
from app.models.analysis_run import AnalysisRun
from app.models.enums import AnalysisRunStatusEnum
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.analytics import AnalysisCreateRequest
from app.services.report_service import ReportService
from app.utils.dates import utcnow

logger = logging.getLogger(__name__)


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.comments = CommentRepository(db)
        self.analysis_repo = AnalysisRepository(db)
        self.sentiment = SentimentAnalyzer()
        self.keywords = KeywordExtractor()
        self.topics = TopicGrouper()
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
        base = (theme or "").strip() or prompt_text.strip()
        normalized = re.sub(r"\s+", " ", base)
        return normalized[:64].rstrip() + ("..." if len(normalized) > 64 else "")

    def _tokenize_scope(self, value: str) -> set[str]:
        return set(re.findall(r"[A-Za-zА-Яа-яЁё0-9-]{4,}", value.lower()))

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

    def _matches_post_scope(self, post_text: str | None, theme: str | None, keywords: list[str] | None) -> bool:
        keywords = keywords or []
        has_post_scope = bool((theme or "").strip() or keywords)
        if not has_post_scope:
            return True

        text = (post_text or "").strip()
        if not text:
            return False

        lowered = text.lower()
        normalized_keywords = [keyword.strip().lower() for keyword in keywords if keyword.strip()]
        if normalized_keywords and any(keyword in lowered for keyword in normalized_keywords):
            return True

        scope_tokens = self._tokenize_scope(" ".join([theme or "", " ".join(normalized_keywords)]))
        post_tokens = self._tokenize_scope(text)
        token_overlap = len(scope_tokens & post_tokens)
        if token_overlap >= 2:
            return True

        topic_score = self.relevance.score_post_topic(text=text, theme=theme, keywords=keywords)
        if normalized_keywords:
            return topic_score >= 0.22
        return topic_score >= 0.18

    def execute_run_sync(self, analysis_run_id: UUID) -> dict:
        run = self.analysis_repo.update_run_status(analysis_run_id, AnalysisRunStatusEnum.running)
        if not run:
            return {"status": "not_found"}
        try:
            platform_filters = (run.filters_json or {}).get("platforms") or []
            source_filters = [UUID(value) for value in ((run.filters_json or {}).get("source_ids") or [])]
            records = self.comments.get_analysis_records(
                run.project_id,
                period_from=run.period_from,
                period_to=run.period_to,
                source_ids=source_filters,
                platforms=platform_filters,
            )
            scoped_records = [
                record
                for record in records
                if self._matches_post_scope(record[1].post_text, run.theme, run.keywords_json or [])
                and not self._is_advertising_post(record[1].post_text)
            ]

            enriched_comments: list[dict] = []
            for comment, post, source in scoped_records:
                extracted_keywords = self.keywords.extract(comment.text)
                topics = self.topics.group(extracted_keywords, comment.text)
                relevance_score = self.relevance.score_comment_prompt(
                    text=comment.text,
                    prompt_text=run.prompt_text,
                )
                sentiment_result = self.sentiment.analyze(comment.text)
                self.analysis_repo.upsert_comment_analysis(
                    comment_id=comment.id,
                    sentiment=sentiment_result["sentiment"],
                    sentiment_score=sentiment_result["score"],
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
                        "sentiment": sentiment_result["sentiment"].value,
                        "sentiment_score": sentiment_result["score"],
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
            )
            summary_text = self.report_service.build_summary_text(report_json, prompt_text=run.prompt_text)
            self.analysis_repo.replace_report_snapshot(run.id, report_json, summary_text)
            self.analysis_repo.update_run_status(run.id, AnalysisRunStatusEnum.completed, finished_at=utcnow())
            return {"status": "completed", "analysis_run_id": str(run.id)}
        except Exception:
            logger.exception("Analytics run failed", extra={"analysis_run_id": str(run.id), "project_id": str(run.project_id)})
            self.analysis_repo.update_run_status(run.id, AnalysisRunStatusEnum.failed, finished_at=utcnow())
            return {"status": "failed", "analysis_run_id": str(run.id)}
