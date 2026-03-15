from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter

from openai import OpenAI
from redis import Redis

from app.analytics.prompt_intent import (
    build_prompt_intent as build_shared_prompt_intent,
    extract_prompt_focus_terms as extract_shared_prompt_focus_terms,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

SUMMARY_CACHE_VERSION = "v2"
SUMMARY_PROMPT_VERSION = "structured-summary-v1"
THEME_CACHE_VERSION = "v2"
THEME_PROMPT_VERSION = "theme-labels-v1"

GENERIC_TOPICS = {
    "Общее обсуждение",
    "Общая реакция",
    "General discussion",
    "General reaction",
}

POST_THEME_STOPWORDS = {
    "это",
    "этот",
    "эта",
    "эти",
    "такой",
    "такая",
    "такие",
    "также",
    "просто",
    "очень",
    "снова",
    "будет",
    "будут",
    "после",
    "между",
    "через",
    "только",
    "сегодня",
    "вчера",
    "завтра",
    "здесь",
    "там",
    "тоже",
    "тогда",
    "потом",
    "если",
    "вот",
    "все",
    "всего",
    "всем",
    "всех",
    "или",
    "для",
    "при",
    "под",
    "над",
    "про",
    "как",
    "что",
    "чтобы",
    "где",
    "когда",
    "было",
    "были",
    "был",
    "была",
    "года",
    "год",
    "лет",
    "месяц",
    "месяца",
    "неделя",
    "недели",
    "день",
    "дня",
    "дней",
    "час",
    "часа",
    "часов",
    "первый",
    "первая",
    "первые",
    "второй",
    "вторая",
    "вторые",
    "третий",
    "третья",
    "новый",
    "новая",
    "новые",
    "старый",
    "старые",
    "самый",
    "самая",
    "самые",
    "свои",
    "свой",
    "своих",
    "наш",
    "наши",
    "ваш",
    "ваши",
    "сказал",
    "сказала",
    "заявил",
    "заявила",
    "сообщил",
    "сообщила",
    "говорит",
    "пишет",
    "россия",
    "россии",
    "москва",
    "москве",
    "область",
    "области",
    "район",
    "района",
    "край",
    "края",
    "новость",
    "новости",
    "пост",
    "посты",
    "публикация",
    "публикации",
    "сообщение",
    "сообщения",
    "обсуждение",
    "обсуждения",
    "реакция",
    "реакции",
    "аудитория",
    "аудитории",
    "комментарий",
    "комментарии",
    "комментариях",
    "telegram",
    "телеграм",
    "vk",
    "канал",
    "канале",
    "каналы",
    "сообщество",
    "сообщества",
    "город",
    "города",
    "городе",
    "люди",
    "людей",
    "жители",
    "житель",
}

VERBISH_THEME_TOKENS = {
    "быть",
    "будет",
    "будут",
    "стал",
    "стала",
    "стали",
    "может",
    "могут",
    "будем",
    "будешь",
    "смогут",
    "работать",
    "отключать",
    "замедлять",
    "вызвать",
    "вызывать",
    "обсуждать",
    "считать",
    "считает",
    "отключают",
    "отключат",
    "отключили",
    "работают",
    "замедляют",
    "замедление",
    "ускоряют",
    "заявить",
    "сообщить",
    "говорить",
    "показать",
    "рассказать",
}

PROMPT_STOPWORDS = POST_THEME_STOPWORDS | {
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
    "найди",
    "найти",
    "покажи",
    "показать",
    "определи",
    "определи",
    "выдели",
    "выяви",
    "расскажи",
    "объясни",
    "сделай",
    "нужно",
    "надо",
    "хочу",
    "над",
    "ли",
    "наиболее",
    "самой",
    "самая",
    "самый",
    "самые",
    "неделю",
}

SOURCE_METRIC_TERMS = {
    "канал",
    "канале",
    "каналы",
    "сообщество",
    "сообщества",
    "источник",
    "источники",
    "аудитория",
    "аудитории",
    "активная",
    "активность",
    "вовлеченность",
    "метрики",
    "охват",
    "охваты",
    "подписчики",
    "подписчиков",
    "подписчик",
    "аудитория канала",
    "размер канала",
    "реакции",
    "реакция",
    "лайки",
    "лайков",
    "репосты",
    "репостов",
    "сравни",
    "сравнить",
}

POST_SCOPE_TERMS = {
    "новость",
    "новости",
    "пост",
    "посты",
    "публикация",
    "публикации",
    "тема",
    "темы",
    "сюжет",
    "сюжеты",
    "обсуждаемая",
    "обсуждаемый",
    "обсуждение",
}

COMMENT_REACTION_TERMS = {
    "комментарий",
    "комментарии",
    "комментариев",
    "реакция",
    "реакции",
    "думают",
    "мнение",
    "отношение",
    "позитив",
    "негатив",
    "эмоции",
    "жалобы",
    "претензии",
    "критикуют",
    "поддерживают",
    "поддержка",
    "тревога",
}

CANONICAL_THEME_PATTERNS: list[tuple[str, str]] = [
    (r"\bинтернет\b.*\bподмосков", "Ограничения интернета в Подмосковье"),
    (r"\bподмосков[а-я]*\b.*\bинтернет", "Ограничения интернета в Подмосковье"),
    (r"\bбел[а-я]*\s+списк", "Сайты из белого списка"),
    (r"\bтелеграм\b.*\bзамедл", "Замедление Telegram"),
    (r"\bтелеграм\b.*\bблокир", "Блокировки Telegram"),
    (r"\bмосковск[а-я]*\b.*\bнедел[а-я]*\b.*\bмод[а-я]*", "Московская неделя моды"),
    (r"\bнедел[а-я]*\b.*\bмод[а-я]*\b.*\bмосковск[а-я]*", "Московская неделя моды"),
    (r"\bподснежник[а-я]*", "Подснежники"),
    (r"\bталон[а-я]*\b.*\bинтернет", "Талоны на интернет"),
    (r"\bинтернет\b.*\bталон[а-я]*", "Талоны на интернет"),
    (r"\bснег", "Уборка снега"),
    (r"\bуборк[а-я]*\b.*\bснег", "Уборка снега"),
    (r"\bблагоустрой", "Благоустройство дворов и общественных пространств"),
    (r"\bдвор", "Благоустройство дворов"),
    (r"\bтротуар", "Ремонт тротуаров"),
    (r"\bфасад", "Ремонт фасадов"),
    (r"\bплощадк", "Детские и общественные площадки"),
    (r"\bпарковк", "Парковка и дворовые проезды"),
    (r"\bдорог", "Дороги и дорожные работы"),
    (r"\bсвяз[ьи]", "Проблемы связи"),
]

THEME_NOISE_TOKENS = {
    "подслушано",
    "тусовки",
    "стабильно",
    "городской",
    "городские",
}

LOCATION_NOISE_ROOTS = {
    "барнаул",
    "москв",
    "подмосков",
    "алтайск",
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


class SummaryGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)

    def generate_summary_bundle(self, report_json: dict, prompt_text: str | None = None) -> tuple[dict, str]:
        summary_payload = self._build_summary_payload(report_json, prompt_text)
        llm_bundle = self._generate_llm_summary_bundle(report_json, prompt_text, summary_payload)
        fallback_takeaways = self._build_takeaways(report_json, summary_payload, prompt_text)
        summary_text = (llm_bundle or {}).get("overview") or self._build_fallback_summary(
            report_json,
            prompt_text,
            summary_payload,
        )
        return {
            "overview": summary_text,
            "takeaways": (llm_bundle or {}).get("takeaways") or fallback_takeaways,
            "confidence_assessment": summary_payload.get("confidence_assessment", {}),
            "theme_reaction_map": summary_payload.get("theme_reaction_map", []),
            "focus_evidence": summary_payload.get("focus_evidence", []),
        }, summary_text

    def generate_summary_text(self, report_json: dict, prompt_text: str | None = None) -> str:
        _bundle, summary_text = self.generate_summary_bundle(report_json, prompt_text=prompt_text)
        return summary_text

    def _reasoning_options(self) -> dict:
        effort = (self.settings.openai_reasoning_effort or "").strip().lower()
        if not effort:
            return {}
        return {"reasoning_effort": effort}

    def _completion_options(self) -> dict:
        options = dict(self._reasoning_options())
        if "reasoning_effort" not in options:
            options["temperature"] = 0
        return options

    def _log_openai_completion(self, completion, purpose: str) -> None:
        usage = getattr(completion, "usage", None)
        logger.info(
            "OpenAI completion succeeded",
            extra={
                "purpose": purpose,
                "requested_model": self.settings.openai_compatible_model,
                "response_model": getattr(completion, "model", None),
                "reasoning_effort": self.settings.openai_reasoning_effort,
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            },
        )

    def _llm_summary_enabled(self, report_json: dict) -> bool:
        analyzed_comments = int(report_json.get("stats", {}).get("analyzed_comments", 0) or 0)
        total_posts = int(report_json.get("stats", {}).get("total_posts", 0) or 0)
        return bool(
            self.settings.llm_summary_enabled
            and self.settings.openai_compatible_base_url
            and self.settings.openai_compatible_api_key
            and (analyzed_comments >= self.settings.llm_summary_min_comments or total_posts > 0)
        )

    def _generate_llm_summary_bundle(
        self,
        report_json: dict,
        prompt_text: str | None,
        summary_payload: dict,
    ) -> dict | None:
        if not self._llm_summary_enabled(report_json):
            return None

        try:
            cache_key = self._build_cache_key(summary_payload)
            cached = self.redis.get(cache_key)
            if cached:
                return self._parse_summary_bundle(cached)

            client = OpenAI(
                base_url=self.settings.openai_compatible_base_url,
                api_key=self.settings.openai_compatible_api_key,
            )
            completion = client.chat.completions.create(
                model=self.settings.openai_compatible_model,
                max_completion_tokens=700,
                messages=[
                    {"role": "system", "content": self._build_structured_summary_system_prompt()},
                    {
                        "role": "user",
                        "content": json.dumps(summary_payload, ensure_ascii=False),
                    },
                ],
                **self._completion_options(),
            )
            self._log_openai_completion(completion, "summary")
            content = (completion.choices[0].message.content or "").strip()
            bundle = self._parse_summary_bundle(content)
            if bundle:
                self.redis.setex(
                    cache_key,
                    self.settings.llm_summary_cache_ttl_seconds,
                    json.dumps(bundle, ensure_ascii=False),
                )
                return bundle
            if content:
                return {"overview": content, "takeaways": []}
        except Exception:
            logger.exception("LLM summary generation failed")

        return None

    def _build_structured_summary_system_prompt(self) -> str:
        return (
            "You prepare the final analytics answer in Russian.\n"
            "Return a valid JSON object only.\n"
            "JSON schema:\n"
            "{\n"
            '  "overview": "string",\n'
            '  "takeaways": ["string", "string"],\n'
            '  "analysis_mode": "string"\n'
            "}\n"
            "Requirements:\n"
            "- overview must directly answer the user prompt in the first sentence.\n"
            "- adapt the answer to the actual request type: source/channel comparison, post/news ranking, theme analysis, comment reaction, mixed analysis.\n"
            "- if analysis_request.theme_of_posts is present, rely only on theme-scoped evidence; do not pull unrelated stories.\n"
            "- if analysis_request.analysis_axes indicates source_metrics without post_scope/comment_reaction, answer at source/channel level, not through one post.\n"
            "- if prompt_mode contains most_discussed_news and top_discussed_posts is not empty, explicitly name the leading post.\n"
            "- use focus_evidence and theme_reaction_map when they are relevant to the prompt.\n"
            "- do not invent themes from raw word fragments or single noisy tokens.\n"
            "- do not mention generic topics like 'general discussion' unless they are truly the only defensible conclusion.\n"
            "- if confidence is low or the evidence is sparse, say that clearly and keep claims narrow.\n"
            "- takeaways must contain 1 to 3 concise points, each useful and tied to the current prompt only.\n"
            "- no markdown fences, no commentary outside JSON."
        )

    def _parse_summary_bundle(self, raw_value: str) -> dict | None:
        text = (raw_value or "").strip()
        if not text:
            return None

        candidate = text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start : end + 1]

        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            return None

        overview = (payload.get("overview") or "").strip()
        if not overview:
            return None

        takeaways: list[str] = []
        for item in payload.get("takeaways", []) or []:
            if not isinstance(item, str):
                continue
            normalized = item.strip()
            if normalized and normalized not in takeaways:
                takeaways.append(normalized)

        return {
            "overview": overview,
            "takeaways": takeaways[:3],
            "analysis_mode": str(payload.get("analysis_mode") or "").strip(),
        }

    def _build_system_prompt(self) -> str:
        return (
            "Ты готовишь итоговую аналитическую сводку по реакции аудитории на новости и посты. "
            "Твоя задача — максимально точно ответить на пользовательский запрос, а не пересказать поля отчета. "
            "Сначала определи, чего именно требует запрос пользователя, используя поля user_prompt, prompt_mode, request_contract, answer_strategy и prompt_focus_terms. "
            "Сформируй внутренний план ответа, но не показывай его. Затем дай конкретный ответ именно на этот запрос. "
            "Опирайся прежде всего на сами посты и новости, а комментарии используй как слой подтверждения: "
            "интерес, негатив, одобрение, претензии, тональность и характер реакции. "
            "Когда речь идет о наиболее обсуждаемых, заметных или интересных новостях, ориентируйся прежде всего на количество комментариев, реакций или лайков и репостов у постов. "
            "Для Telegram поле likes_count в payload означает количество реакций на посте, для VK — количество лайков. "
            "Если пользователь спрашивает о самой обсуждаемой новости, назови ее прямо и объясни, почему она самая обсуждаемая "
            "(число комментариев, реакций или лайков, репостов, вовлеченность, характер реакции). "
            "Первое содержательное предложение должно сразу отвечать на пользовательский запрос, без вводных фраз вроде 'по выборке видна картина' или 'в целом можно сказать'. "
            "Если answer_strategy указывает на один конкретный объект или один главный вывод, начни текст именно с него. "
            "Если answer_strategy указывает на сравнение или ранжирование, строй ответ вокруг сравнения или ранжирования, а не вокруг общей статистики. "
            "Если пользователь спрашивает о темах, выделяй только темы, которые реально подтверждаются несколькими постами или ключевыми постами выборки. "
            "Если в payload есть focus_evidence, используй его как основной слой доказательств для того, какие сюжеты ближе всего к формулировке пользовательского запроса. "
            "Если в payload есть theme_reaction_map, используй его как готовую карту связок тема -> интерес -> тип реакции аудитории. "
            "Если confidence_assessment = low, говори осторожно, не делай сильных обобщений и не приписывай всей аудитории устойчивую позицию без прямой опоры в данных. "
            "При low confidence опирайся на конкретные посты и конкретные комментарии, а не на широкие формулировки уровня всего информационного поля. "
            "Не используй мусорные формулировки вроде 'Общее обсуждение', если они не помогают ответить на вопрос. "
            "Не придумывай темы из одиночных слов без смысловой опоры. "
            "Ответ должен быть четким, структурированным и полезным для заказчика. "
            "Подзаголовки допустимы, но только если они делают ответ понятнее. "
            "Избегай воды, общих фраз и простого пересказа процентов без выводов. "
            "Не ограничивайся перечислением процентов. Всегда объясняй, какие именно новости, темы или сюжеты стоят за выводом. "
            "Если данных мало, прямо обозначь ограничение, но все равно ответь максимально предметно."
        )

    def _build_cache_key(self, summary_payload: dict) -> str:
        digest = hashlib.sha256(
            json.dumps(summary_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        effort = (self.settings.openai_reasoning_effort or "").strip().lower() or "none"
        return (
            f"summary-cache:{SUMMARY_CACHE_VERSION}:{SUMMARY_PROMPT_VERSION}:"
            f"{self.settings.openai_compatible_model}:{effort}:{digest}"
        )

    def _build_theme_cache_key(self, payload: dict) -> str:
        digest = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        effort = (self.settings.openai_reasoning_effort or "").strip().lower() or "none"
        return (
            f"theme-label-cache:{THEME_CACHE_VERSION}:{THEME_PROMPT_VERSION}:"
            f"{self.settings.openai_compatible_model}:{effort}:{digest}"
        )

    def _build_summary_payload(self, report_json: dict, prompt_text: str | None) -> dict:
        examples = report_json.get("examples", {})
        posts = report_json.get("posts", {})
        matched_posts = (posts.get("matched", []) or [])[:8]
        top_popular = (posts.get("top_popular", []) or [])[:5]
        top_unpopular = (posts.get("top_unpopular", []) or [])[:5]
        source_comparison = (report_json.get("sources", {}).get("comparison", []) or [])[:8]
        declared_theme = (report_json.get("meta", {}).get("post_theme") or "").strip() or None
        has_explicit_scope = bool(declared_theme or report_json.get("meta", {}).get("post_keywords"))
        prompt_intent = build_shared_prompt_intent(prompt_text, has_explicit_scope=has_explicit_scope)
        analysis_axes = prompt_intent.analysis_axes
        theme_scoped_posts = self._filter_posts_for_declared_theme(
            matched_posts + top_popular + top_unpopular,
            declared_theme,
        )
        theme_basis_posts = theme_scoped_posts if declared_theme else (matched_posts + top_popular + top_unpopular)
        top_discussed = sorted(
            theme_scoped_posts if declared_theme else (theme_scoped_posts or matched_posts),
            key=lambda post: (post.get("comments_count", 0), post.get("score", 0)),
            reverse=True,
        )[:5]
        max_examples = max(self.settings.llm_summary_max_examples_per_bucket, 2)

        meaningful_topics = [
            topic
            for topic in (report_json.get("topics", []) or [])
            if (topic.get("name") or "").strip() not in GENERIC_TOPICS
        ][: self.settings.llm_summary_max_topics]

        heuristic_post_themes = self._extract_post_theme_candidates(
            theme_basis_posts,
            prompt_text=prompt_text,
            declared_theme=declared_theme,
        )
        derived_post_themes = self._extract_post_themes_with_llm(
            matched_posts=theme_basis_posts if declared_theme else matched_posts,
            top_popular=[] if declared_theme else top_popular,
            top_unpopular=[] if declared_theme else top_unpopular,
            prompt_text=prompt_text,
            declared_theme=declared_theme,
            heuristic_themes=heuristic_post_themes,
        )
        prompt_mode = prompt_intent.prompt_mode
        prompt_focus_terms = prompt_intent.focus_terms

        return {
            "analysis_request": {
                "theme_of_posts": (report_json.get("meta", {}).get("post_theme") or "").strip() or None,
                "declared_theme_present": bool(declared_theme),
                "has_explicit_scope": has_explicit_scope,
                "keywords_for_posts": report_json.get("meta", {}).get("post_keywords", []),
                "user_prompt": (prompt_text or "").strip(),
                "analysis_axes": analysis_axes,
                "prompt_mode": prompt_mode,
                "request_contract": prompt_intent.request_contract,
                "answer_strategy": prompt_intent.answer_strategy,
                "prompt_focus_terms": prompt_focus_terms,
                "period_from": report_json.get("meta", {}).get("period_from"),
                "period_to": report_json.get("meta", {}).get("period_to"),
                "platforms": report_json.get("meta", {}).get("platforms", []),
            },
            "coverage": report_json.get("stats", {}),
            "selection_context": {
                "matched_posts_count": len(matched_posts),
                "theme_scoped_posts_count": len(theme_scoped_posts),
                "selected_sources_count": len(source_comparison),
            },
            "confidence_assessment": self._build_confidence_assessment(report_json),
            "sentiment_distribution": report_json.get("sentiment", {}),
            "derived_post_themes": derived_post_themes,
            "heuristic_post_themes": heuristic_post_themes,
            "theme_reaction_map": self._build_theme_reaction_map(
                derived_post_themes,
                theme_basis_posts if declared_theme else matched_posts,
                [] if declared_theme else top_popular,
                [] if declared_theme else top_unpopular,
            ),
            "comment_topics": meaningful_topics,
            "focus_evidence": self._build_prompt_focus_evidence(
                prompt_focus_terms,
                theme_scoped_posts if declared_theme else matched_posts,
                [] if declared_theme else top_popular,
                [] if declared_theme else top_unpopular,
            ),
            "source_comparison_map": source_comparison,
            "positive_signals": {
                "patterns": report_json.get("insights", {}).get("liked_patterns", []),
                "topics": self._extract_comment_signal_topics(report_json, "positive"),
                "examples": (examples.get("positive_comments", []) or [])[:max_examples],
            },
            "negative_signals": {
                "patterns": report_json.get("insights", {}).get("disliked_patterns", []),
                "topics": self._extract_comment_signal_topics(report_json, "negative"),
                "examples": (examples.get("negative_comments", []) or [])[:max_examples],
            },
            "neutral_signals": {
                "examples": (examples.get("neutral_comments", []) or [])[:max_examples],
            },
            "matched_posts": [self._compact_post(post) for post in matched_posts],
            "top_discussed_posts": [self._compact_post(post) for post in top_discussed],
            "theme_scoped_posts": [self._compact_post(post) for post in (theme_scoped_posts[:8] if theme_scoped_posts else [])],
            "top_popular_posts": [self._compact_post(post) for post in top_popular],
            "top_unpopular_posts": [self._compact_post(post) for post in top_unpopular],
        }

    def _filter_posts_for_declared_theme(self, posts: list[dict], declared_theme: str | None) -> list[dict]:
        if not declared_theme:
            return []
        unique: list[dict] = []
        seen: set[str] = set()
        for post in posts:
            post_id = str(post.get("post_id") or "")
            if post_id and post_id in seen:
                continue
            if self._theme_matches_post(declared_theme, post):
                unique.append(post)
                if post_id:
                    seen.add(post_id)
        return unique

    def _extract_post_themes_with_llm(
        self,
        matched_posts: list[dict],
        top_popular: list[dict],
        top_unpopular: list[dict],
        prompt_text: str | None,
        declared_theme: str | None,
        heuristic_themes: list[str],
    ) -> list[str]:
        llm_enabled = (
            self.settings.llm_summary_enabled
            and self.settings.openai_compatible_base_url
            and self.settings.openai_compatible_api_key
        )
        posts = (matched_posts + top_popular + top_unpopular)[:8]
        if not llm_enabled or not posts:
            return heuristic_themes

        payload = {
            "prompt_text": (prompt_text or "").strip(),
            "declared_theme": declared_theme,
            "heuristic_themes": heuristic_themes,
            "posts": [
                {
                    "post_text": self._prepare_post_text_for_theme_llm(post.get("post_text") or ""),
                    "comments_count": int(post.get("comments_count", 0) or 0),
                    "likes_count": int(post.get("likes_count", 0) or 0),
                    "reposts_count": int(post.get("reposts_count", 0) or 0),
                }
                for post in posts
            ],
        }
        cache_key = self._build_theme_cache_key(payload)
        cached = self.redis.get(cache_key)
        if cached:
            try:
                value = json.loads(cached)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, str)][:6] or heuristic_themes
            except json.JSONDecodeError:
                pass

        try:
            client = OpenAI(
                base_url=self.settings.openai_compatible_base_url,
                api_key=self.settings.openai_compatible_api_key,
            )
            completion = client.chat.completions.create(
                model=self.settings.openai_compatible_model,
                max_completion_tokens=180,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are naming themes for a Russian-language media analytics report. "
                            "Return only a JSON array with 3 to 6 short Russian theme labels. "
                            "Each label must be a clean editorial theme title, not a raw fragment of a headline. "
                            "Use 2 to 5 words, prefer noun phrases, avoid imperative wording, avoid duplicates, "
                            "avoid channel names, city names, filler words, dates, and generic words like post, news, discussion. "
                            "If several posts describe the same story, merge them into one theme. "
                            "Bad labels: '???????? ????????????? ????', '????????? ??????', '?????????? ???????'. "
                            "Good labels: '????????? ???? ? ????????? ??????', '??????????? ? ?????? ?? ????', "
                            "'??????????? ????????? ? ???????????'. "
                            "If the request already contains a theme or focus, prefer themes directly related to that request."
                        ),
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                **self._completion_options(),
            )
            self._log_openai_completion(completion, "theme_extraction")
            content = (completion.choices[0].message.content or "").strip()
            if content:
                parsed = json.loads(content)
                if isinstance(parsed, list):
                    themes = []
                    for item in parsed:
                        if not isinstance(item, str):
                            continue
                        cleaned = self._normalize_single_theme(item)
                        if cleaned and cleaned not in themes:
                            themes.append(cleaned)
                    if themes:
                        themes = self._dedupe_theme_list(themes)
                        self.redis.setex(cache_key, self.settings.llm_summary_cache_ttl_seconds, json.dumps(themes, ensure_ascii=False))
                        return themes[:6]
        except Exception:
            logger.exception("LLM theme extraction failed")

        return heuristic_themes

    def _build_confidence_assessment(self, report_json: dict) -> dict:
        stats = report_json.get("stats", {})
        total_posts = int(stats.get("total_posts", 0) or 0)
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)

        if total_posts >= 8 and analyzed_comments >= 40:
            return {
                "level": "high",
                "reason": "В выборке достаточно постов и релевантных комментариев для уверенного вывода.",
            }
        if total_posts >= 4 and analyzed_comments >= 15:
            return {
                "level": "medium",
                "reason": "Данных достаточно для предварительных выводов, но отдельные темы могут быть представлены неравномерно.",
            }
        return {
            "level": "low",
            "reason": "Данных мало, поэтому выводы стоит считать предварительными и использовать с осторожностью.",
        }

    def _build_theme_reaction_map(
        self,
        themes: list[str],
        matched_posts: list[dict],
        top_popular_posts: list[dict],
        top_unpopular_posts: list[dict],
    ) -> list[dict]:
        posts = matched_posts or top_popular_posts or top_unpopular_posts
        result: list[dict] = []
        seen_signatures: list[set[str]] = []
        used_leading_posts: set[str] = set()
        for theme in themes[:6]:
            matching = [post for post in posts if self._theme_matches_post(theme, post)]
            if not matching:
                continue
            comments_total = sum(int(post.get("comments_count", 0) or 0) for post in matching)
            likes_total = sum(int(post.get("likes_count", 0) or 0) for post in matching)
            reposts_total = sum(int(post.get("reposts_count", 0) or 0) for post in matching)
            positive_total = sum(int(post.get("positive_relevant_comments_count", 0) or 0) for post in matching)
            negative_total = sum(int(post.get("negative_relevant_comments_count", 0) or 0) for post in matching)
            neutral_total = sum(int(post.get("neutral_relevant_comments_count", 0) or 0) for post in matching)
            leader = sorted(
                matching,
                key=lambda post: (
                    int(post.get("comments_count", 0) or 0),
                    int(post.get("likes_count", 0) or 0),
                    int(post.get("reposts_count", 0) or 0),
                    float(post.get("score", 0) or 0),
                ),
                reverse=True,
            )[0]
            theme_label = self._normalize_theme_for_display(theme, matching)
            if not theme_label:
                continue
            leader_id = str(leader.get("post_id") or "")
            signature = self._theme_signature(theme_label)
            if leader_id and leader_id in used_leading_posts:
                continue
            if signature and any(self._theme_signatures_overlap(signature, existing) for existing in seen_signatures):
                continue
            result.append(
                {
                    "theme": theme_label,
                    "platform": leader.get("platform"),
                    "posts_count": len(matching),
                    "comments_count": comments_total,
                    "likes_count": likes_total,
                    "reposts_count": reposts_total,
                    "interest_level": self._engagement_label(comments_total, likes_total, reposts_total),
                    "reaction_tendency": self._reaction_label(positive_total, negative_total, neutral_total),
                    "positive_comments": positive_total,
                    "negative_comments": negative_total,
                    "neutral_comments": neutral_total,
                    "leading_post": self._compact_post(leader),
                }
            )
            if signature:
                seen_signatures.append(signature)
            if leader_id:
                used_leading_posts.add(leader_id)
        return result

    def _build_prompt_focus_evidence(
        self,
        focus_terms: list[str],
        matched_posts: list[dict],
        top_popular_posts: list[dict],
        top_unpopular_posts: list[dict],
    ) -> list[dict]:
        if not focus_terms:
            return []

        candidates = matched_posts + top_popular_posts + top_unpopular_posts
        seen: set[str] = set()
        scored: list[tuple[tuple[int, int, int, float], dict]] = []

        for post in candidates:
            post_id = str(post.get("post_id") or "")
            if post_id and post_id in seen:
                continue
            if post_id:
                seen.add(post_id)

            text = self._normalize_text(post.get("post_text") or "")
            matched_terms = [term for term in focus_terms if self._term_matches_text(term, text)]
            if not matched_terms:
                continue

            rank = (
                len(matched_terms),
                int(post.get("comments_count", 0) or 0),
                int(post.get("likes_count", 0) or 0) + int(post.get("reposts_count", 0) or 0),
                float(post.get("score", 0) or 0),
            )
            scored.append(
                (
                    rank,
                    {
                        "matched_terms": matched_terms,
                        "post": self._compact_post(post),
                    },
                )
            )

        scored.sort(key=lambda item: item[0], reverse=True)
        return [payload for _, payload in scored[:5]]

    def _infer_analysis_axes(self, prompt_text: str | None) -> list[str]:
        return build_shared_prompt_intent(prompt_text).analysis_axes

        prompt = self._normalize_text(prompt_text or "")
        if not prompt:
            return ["general"]

        axes: list[str] = []
        if any(term in prompt for term in SOURCE_METRIC_TERMS):
            axes.append("source_metrics")
        if any(term in prompt for term in POST_SCOPE_TERMS):
            axes.append("post_scope")
        if any(term in prompt for term in COMMENT_REACTION_TERMS):
            axes.append("comment_reaction")

        return axes or ["general"]

    def _infer_prompt_mode(self, prompt_text: str | None) -> list[str]:
        return build_shared_prompt_intent(prompt_text).prompt_mode

        prompt = self._normalize_text(prompt_text or "")
        modes: list[str] = []
        patterns = [
            (r"сам[а-я]* обсужда", "most_discussed_news"),
            (r"наиболее обсужда", "most_discussed_news"),
            (r"какая новость", "specific_news_answer"),
            (r"какие новости", "specific_news_answer"),
            (r"в каком канале|какой канал|какое сообщество|какой источник", "source_comparison"),
            (r"активн[а-я]* аудитори", "source_comparison"),
            (r"сравн.*канал|сравн.*сообществ|сравн.*источник", "source_comparison"),
            (r"интерес|вовлеч|резонанс", "interest_analysis"),
            (r"негатив|эмоци|критик|возмущ|раздраж", "negative_analysis"),
            (r"позитив|нрав|одобр|поддерж", "positive_analysis"),
            (r"тем[аы]|сюжет", "theme_analysis"),
            (r"сравн|отлич|разниц", "comparison"),
            (r"причин|почему", "causal_explanation"),
            (r"поддержива|одобря|хвал|благодар", "support_analysis"),
            (r"жалоб|претензи|критикуют|ругают|недоволь", "complaints_analysis"),
            (r"опасени|тревог|боят|страх|риски", "concerns_analysis"),
            (r"конфликт|спор|поляриз|раздел", "polarization_analysis"),
            (r"главн|ключев|основн.*вывод", "takeaways_analysis"),
        ]
        for pattern, mode in patterns:
            if re.search(pattern, prompt) and mode not in modes:
                modes.append(mode)
        return modes or ["general_analysis"]

    def _infer_request_contract(self, prompt_text: str | None) -> list[str]:
        return build_shared_prompt_intent(prompt_text).request_contract

        modes = self._infer_prompt_mode(prompt_text)
        instructions: list[str] = []

        if "most_discussed_news" in modes:
            instructions.append(
                "Определи конкретную новость или пост с наибольшим объемом обсуждения и объясни, по каким признакам она лидирует."
            )
        if "source_comparison" in modes:
            instructions.append(
                "Сравни каналы, сообщества или источники между собой и назови, где аудитория активнее по совокупности комментариев, реакций или лайков и репостов."
            )
        if "interest_analysis" in modes:
            instructions.append(
                "Определи, какие темы и новости вызывают наибольший интерес аудитории."
            )
        if "negative_analysis" in modes:
            instructions.append(
                "Определи, какие темы и новости вызывают негативные эмоции или критику."
            )
        if "positive_analysis" in modes:
            instructions.append(
                "Определи, какие темы и сюжеты аудитория воспринимает скорее позитивно."
            )
        if "support_analysis" in modes:
            instructions.append(
                "Определи, какие решения, сюжеты или действия аудитория поддерживает или одобряет."
            )
        if "complaints_analysis" in modes:
            instructions.append(
                "Определи, на что именно люди жалуются и в чем состоят основные претензии."
            )
        if "concerns_analysis" in modes:
            instructions.append(
                "Определи, что вызывает тревогу, опасения или настороженность аудитории."
            )
        if "polarization_analysis" in modes:
            instructions.append(
                "Покажи, где мнения аудитории расходятся и какие сюжеты вызывают полярную реакцию."
            )
        if "theme_analysis" in modes:
            instructions.append(
                "Выдели реальные темы самих новостей и постов, а не случайные слова из комментариев."
            )
        if "comparison" in modes:
            instructions.append(
                "Сравни реакцию аудитории между основными темами и объясни различия."
            )
        if "causal_explanation" in modes:
            instructions.append(
                "Объясни причины реакции аудитории на основе содержания постов и комментариев."
            )
        if "takeaways_analysis" in modes:
            instructions.append(
                "Сформулируй главные содержательные выводы, а не только перечисление метрик."
            )

        if not instructions:
            instructions.append(
                "Дай конкретный аналитический ответ на запрос пользователя, опираясь на темы постов и реакцию аудитории."
            )
        return instructions

    def _build_answer_strategy(self, prompt_text: str | None, analysis_axes: list[str] | None = None) -> dict:
        return build_shared_prompt_intent(prompt_text).answer_strategy

        prompt = self._normalize_text(prompt_text or "")
        axes = set(analysis_axes or [])
        response_shape = "analysis_note"
        first_sentence_rule = "Начни с прямого ответа на пользовательский запрос."
        must_cover: list[str] = []

        if re.search(r"сам[а-я]* обсужда|наиболее обсужда", prompt):
            response_shape = "single_lead_item"
            first_sentence_rule = "Начни с самой обсуждаемой новости или поста и назови ее прямо в первом предложении."
            must_cover.extend(
                [
                    "Назови конкретную новость или пост-лидер.",
                    "Объясни, почему именно этот сюжет стал самым обсуждаемым.",
                ]
            )
        elif re.search(r"в каком канале|какой канал|какое сообщество|какой источник|активн[а-я]* аудитори|сравн.*канал|сравн.*сообществ|сравн.*источник", prompt):
            response_shape = "source_comparison"
            first_sentence_rule = "Сразу назови канал или сообщество с самой активной аудиторией и объясни, по каким метрикам он лидирует."
            must_cover.extend(
                [
                    "Назови канал или сообщество-лидер.",
                    "Сравни его с другими источниками по комментариям, реакциям или лайкам и репостам.",
                ]
            )
        elif re.search(r"топ|рейтинг|какие новости|какие темы", prompt):
            response_shape = "ranked_or_grouped_answer"
            first_sentence_rule = "Сразу назови ключевые темы или лидирующие новости, без вступительной воды."
            must_cover.append("Сгруппируй или ранжируй ключевые темы и новости по смыслу запроса.")

        if re.search(r"сравн|разниц|отлич", prompt):
            response_shape = "comparison"
            first_sentence_rule = "Сначала назови главную разницу между объектами сравнения."
            must_cover.append("Покажи различия между темами, сюжетами или типами реакции.")

        if re.search(r"почему|причин", prompt):
            must_cover.append("Объясни причины реакции аудитории, а не только факт реакции.")

        if re.search(r"интерес|вовлеч|резонанс", prompt):
            must_cover.append("Ответь, что именно вызывает интерес аудитории.")

        if re.search(r"негатив|эмоци|критик|возмущ|раздраж", prompt):
            must_cover.append("Ответь, что именно вызывает негативные эмоции.")

        if re.search(r"позитив|нрав|одобр|поддерж", prompt):
            must_cover.append("Ответь, что аудитория воспринимает позитивно.")

        if re.search(r"жалоб|претензи|недоволь|ругают", prompt):
            must_cover.append("Покажи основные жалобы и претензии аудитории.")

        if re.search(r"опасени|тревог|боят|страх|риски", prompt):
            must_cover.append("Покажи, какие риски и опасения люди видят в обсуждаемых сюжетах.")

        if re.search(r"конфликт|спор|поляриз|раздел", prompt):
            must_cover.append("Покажи, какие темы вызывают наиболее полярную реакцию.")

        if re.search(r"вывод|итог|резюме", prompt):
            must_cover.append("Сформулируй короткий содержательный итог по запросу.")

        if not must_cover:
            must_cover.append("Дай максимально прямой и полезный ответ на пользовательский запрос.")

        return {
            "response_shape": response_shape,
            "first_sentence_rule": first_sentence_rule,
            "must_cover": must_cover,
        }

    def _extract_prompt_focus_terms(self, prompt_text: str | None) -> list[str]:
        return extract_shared_prompt_focus_terms(prompt_text)

        prompt = self._normalize_text(prompt_text or "")
        if not prompt:
            return []
        tokens = re.findall(r"[a-zа-я0-9-]{4,}", prompt)
        seen: list[str] = []
        for token in tokens:
            if token in PROMPT_STOPWORDS:
                continue
            if token not in seen:
                seen.append(token)
        return [self._titleize_phrase(token) for token in seen[:8]]

    def _extract_post_theme_candidates(
        self,
        posts: list[dict],
        prompt_text: str | None = None,
        declared_theme: str | None = None,
    ) -> list[str]:
        if len(posts) < 2:
            return self._fallback_theme_candidates(posts, prompt_text, declared_theme)

        unigram_counter: Counter[str] = Counter()
        bigram_counter: Counter[str] = Counter()
        trigram_counter: Counter[str] = Counter()
        corpus_parts: list[str] = []

        for post in posts:
            text = self._normalize_text(post.get("post_text") or "")
            if text:
                corpus_parts.append(text)
            for sentence in self._split_into_sentences(text):
                tokens = [token for token in re.findall(r"[a-zа-я0-9-]{3,}", sentence) if not token.isdigit()]
                filtered = [token for token in tokens if self._is_theme_token(token)]

                unique_tokens = list(dict.fromkeys(filtered))
                for token in unique_tokens:
                    unigram_counter[token] += 1

                seen_bigrams: set[str] = set()
                for left, right in zip(filtered, filtered[1:]):
                    if left == right or not self._is_theme_phrase((left, right)):
                        continue
                    phrase = f"{left} {right}"
                    if phrase in seen_bigrams:
                        continue
                    seen_bigrams.add(phrase)
                    bigram_counter[phrase] += 1

                seen_trigrams: set[str] = set()
                for first, second, third in zip(filtered, filtered[1:], filtered[2:]):
                    phrase_tokens = (first, second, third)
                    if not self._is_theme_phrase(phrase_tokens):
                        continue
                    phrase = " ".join(phrase_tokens)
                    if phrase in seen_trigrams:
                        continue
                    seen_trigrams.add(phrase)
                    trigram_counter[phrase] += 1

        themes: list[str] = []
        for phrase, count in trigram_counter.most_common(16):
            if count < 2:
                continue
            title = self._titleize_phrase(phrase)
            if title not in themes:
                themes.append(title)
            if len(themes) >= 4:
                break

        for phrase, count in bigram_counter.most_common(16):
            if count < 2:
                continue
            title = self._titleize_phrase(phrase)
            if title not in themes:
                themes.append(title)
            if len(themes) >= 5:
                break

        if len(themes) < 5:
            for token, count in unigram_counter.most_common(24):
                if count < 2 or len(token) < 4:
                    continue
                title = self._titleize_phrase(token)
                if title not in themes:
                    themes.append(title)
                if len(themes) >= 8:
                    break

        normalized = self._normalize_theme_candidates(
            themes,
            " ".join(corpus_parts),
            prompt_text=prompt_text,
            declared_theme=declared_theme,
        )
        return normalized[:8]

    def _fallback_theme_candidates(
        self,
        posts: list[dict],
        prompt_text: str | None = None,
        declared_theme: str | None = None,
    ) -> list[str]:
        corpus = " ".join(self._normalize_text(post.get("post_text") or "") for post in posts)
        normalized = self._normalize_theme_candidates([], corpus, prompt_text=prompt_text, declared_theme=declared_theme)
        return normalized[:5]

    def _normalize_theme_candidates(
        self,
        raw_themes: list[str],
        corpus_text: str,
        prompt_text: str | None = None,
        declared_theme: str | None = None,
    ) -> list[str]:
        normalized: list[str] = []

        for pattern, label in CANONICAL_THEME_PATTERNS:
            if re.search(pattern, corpus_text) and label not in normalized:
                normalized.append(label)

        for theme in raw_themes:
            cleaned = self._normalize_single_theme(theme)
            if cleaned and cleaned not in normalized:
                normalized.append(cleaned)

        if declared_theme:
            theme_label = self._normalize_single_theme(declared_theme)
            if theme_label and theme_label not in normalized:
                normalized.append(theme_label)

        for focus in self._extract_prompt_focus_terms(prompt_text):
            focus_label = self._normalize_single_theme(focus)
            if focus_label and focus_label not in normalized:
                normalized.append(focus_label)

        return normalized

    def _normalize_single_theme(self, theme: str) -> str | None:
        text = self._normalize_text(theme)
        if not text:
            return None

        for pattern, label in CANONICAL_THEME_PATTERNS:
            if re.search(pattern, text):
                return label

        tokens = [
            token
            for token in re.findall(r"[a-z?-?0-9-]{4,}", text)
            if self._is_theme_token(token) and token not in THEME_NOISE_TOKENS
        ]
        if not tokens:
            return None

        if len(tokens) > 1:
            tokens = [
                token
                for token in tokens
                if self._stem_token(token) not in LOCATION_NOISE_ROOTS and token not in THEME_NOISE_TOKENS
            ] or tokens

        if len(tokens) >= 3:
            tokens = tokens[:3]
        if len(tokens) == 2 and all(self._looks_like_verb(token) for token in tokens):
            return None

        phrase = " ".join(tokens)
        phrase = self._titleize_phrase(phrase)

        weak_phrases = {
            "???????? ??????????? ????",
            "??????????? ????",
            "????????? ????????",
            "???????? ???????????",
            "???????? ????????? ??????????",
            "????????? ?????????? ???????",
            "????? ?????? ??????????",
        }
        if phrase in weak_phrases:
            return None
        return phrase

    def _normalize_theme_for_display(self, theme: str, matching_posts: list[dict]) -> str | None:
        cleaned = self._normalize_single_theme(theme)
        if not cleaned:
            return None

        if len(cleaned.split()) >= 2 and not any(self._looks_like_verb(token.lower()) for token in cleaned.split()):
            return cleaned

        corpus = " ".join(self._normalize_text(post.get("post_text") or "") for post in matching_posts)
        for pattern, label in CANONICAL_THEME_PATTERNS:
            if re.search(pattern, corpus):
                return label

        leader = matching_posts[0] if matching_posts else None
        if not leader:
            return cleaned

        leader_text = self._prepare_post_text_for_theme_llm(leader.get("post_text") or "")
        title = self._extract_title_phrase(leader_text)
        title = self._normalize_single_theme(title or "")
        return title or cleaned

    def _prepare_post_text_for_theme_llm(self, text: str) -> str:
        prepared = re.sub(r"https?://\S+|t\.me/\S+|vk\.com/\S+", " ", text)
        prepared = re.sub(r"[@#]\S+", " ", prepared)
        prepared = re.sub(r"[^\w\s.,!??-??-???-]", " ", prepared)
        prepared = re.sub(r"\s+", " ", prepared).strip()
        prepared = self._strip_theme_noise_suffix(prepared)
        prepared = self._extract_title_phrase(prepared) or prepared
        return self._shorten(prepared, limit=180)

    def _strip_theme_noise_suffix(self, text: str) -> str:
        tokens = text.split()
        while tokens:
            normalized = self._normalize_text(tokens[-1]).strip(".,!?")
            if normalized in THEME_NOISE_TOKENS or normalized in POST_THEME_STOPWORDS:
                tokens.pop()
                continue
            break
        return " ".join(tokens).strip()

    def _extract_title_phrase(self, text: str) -> str:
        sentence = self._split_into_sentences(text)[0].strip()
        sentence = re.sub(r"\s*[?-]\s*??????????.*$", "", sentence, flags=re.IGNORECASE)
        sentence = re.sub(r"\s{2,}", " ", sentence).strip(" .,!?:;-")
        if "," in sentence:
            parts = [part.strip() for part in sentence.split(",") if part.strip()]
            if parts:
                sentence = max(parts, key=len)
        return sentence

    def _theme_signature(self, theme: str) -> set[str]:
        return {
            self._stem_token(token)
            for token in re.findall(r"[a-z?-?0-9-]{4,}", self._normalize_text(theme))
            if token not in POST_THEME_STOPWORDS and token not in THEME_NOISE_TOKENS
        }

    def _theme_signatures_overlap(self, left: set[str], right: set[str]) -> bool:
        if not left or not right:
            return False
        overlap = left & right
        if len(overlap) >= min(len(left), len(right)):
            return True
        return len(overlap) >= 2

    def _dedupe_theme_list(self, themes: list[str]) -> list[str]:
        ordered: list[str] = []
        signatures: list[set[str]] = []
        for theme in themes:
            signature = self._theme_signature(theme)
            if signature and any(self._theme_signatures_overlap(signature, existing) for existing in signatures):
                continue
            ordered.append(theme)
            if signature:
                signatures.append(signature)
        return ordered

    def _split_into_sentences(self, text: str) -> list[str]:
        chunks = [chunk.strip() for chunk in re.split(r"[.!?…:\n\r]+", text) if chunk.strip()]
        return chunks or [text]

    def _is_theme_token(self, token: str) -> bool:
        if token in POST_THEME_STOPWORDS or token in VERBISH_THEME_TOKENS or token in THEME_NOISE_TOKENS:
            return False
        if len(token) < 4:
            return False
        if self._looks_like_verb(token):
            return False
        return True

    def _is_theme_phrase(self, tokens: tuple[str, ...]) -> bool:
        if any(not self._is_theme_token(token) for token in tokens):
            return False
        if len(set(tokens)) != len(tokens):
            return False
        return any(not self._looks_like_adjective(token) for token in tokens)

    def _looks_like_verb(self, token: str) -> bool:
        verb_endings = (
            "ать",
            "ять",
            "еть",
            "ить",
            "ыть",
            "уть",
            "ться",
            "ти",
            "чь",
            "ется",
            "утся",
            "ются",
            "ится",
            "атся",
            "ятся",
            "ет",
            "ут",
            "ют",
            "ит",
            "ат",
            "ят",
        )
        if token in VERBISH_THEME_TOKENS:
            return True
        return token.endswith(verb_endings)

    def _looks_like_adjective(self, token: str) -> bool:
        adjective_endings = (
            "ый",
            "ий",
            "ой",
            "ая",
            "ое",
            "ые",
            "ого",
            "ему",
            "ому",
            "ыми",
            "ими",
            "ую",
            "яя",
            "ее",
        )
        return token.endswith(adjective_endings)

    def _extract_comment_signal_topics(self, report_json: dict, bucket: str) -> list[str]:
        example_key = {
            "positive": "positive_comments",
            "negative": "negative_comments",
            "neutral": "neutral_comments",
        }.get(bucket, "")

        counter: Counter[str] = Counter()
        for example in (report_json.get("examples", {}).get(example_key, []) or []):
            text = self._normalize_text(example.get("text") or "")
            tokens = [
                token
                for token in re.findall(r"[a-zа-я0-9-]{4,}", text)
                if token not in POST_THEME_STOPWORDS
            ]
            for token in set(tokens):
                counter[token] += 1

        extracted = [self._titleize_phrase(token) for token, _ in counter.most_common(8)]
        fallback = [
            (topic.get("name") or "").strip()
            for topic in (report_json.get("topics", []) or [])
            if (topic.get("name") or "").strip() not in GENERIC_TOPICS
        ]

        ordered: list[str] = []
        for item in extracted + fallback:
            if item and item not in ordered:
                ordered.append(item)
        return ordered[:6]

    def _compact_post(self, post: dict) -> dict:
        return {
            "post_id": post.get("post_id"),
            "post_url": post.get("post_url"),
            "post_text": self._shorten(post.get("post_text") or "", limit=220),
            "platform": post.get("platform"),
            "comments_count": post.get("comments_count", 0),
            "relevant_comments_count": post.get("relevant_comments_count", 0),
            "positive_relevant_comments_count": post.get("positive_relevant_comments_count", 0),
            "negative_relevant_comments_count": post.get("negative_relevant_comments_count", 0),
            "neutral_relevant_comments_count": post.get("neutral_relevant_comments_count", 0),
            "likes_count": post.get("likes_count", 0),
            "reposts_count": post.get("reposts_count", 0),
            "reaction_tendency": self._reaction_label(
                int(post.get("positive_relevant_comments_count", 0) or 0),
                int(post.get("negative_relevant_comments_count", 0) or 0),
                int(post.get("neutral_relevant_comments_count", 0) or 0),
            ),
        }

    def _engagement_metric_label(self, post: dict) -> str:
        platform = (post.get("platform") or "") or ((post.get("leading_post") or {}).get("platform") or "")
        return "реакций" if platform == "telegram" else "лайков"

    def _filter_prompt_related_themes(
        self,
        themes: list[dict],
        focus_evidence: list[dict],
        prompt_focus_terms: list[str],
    ) -> list[dict]:
        if not themes:
            return []

        focus_post_ids = {
            str(item.get("post", {}).get("post_id") or "")
            for item in focus_evidence
            if item.get("post", {}).get("post_id")
        }
        normalized_terms = [self._normalize_text(term) for term in prompt_focus_terms if term]
        filtered: list[dict] = []

        for item in themes:
            leading_post = item.get("leading_post") or {}
            if str(leading_post.get("post_id") or "") in focus_post_ids:
                filtered.append(item)
                continue

            theme_text = self._normalize_text(item.get("theme") or "")
            if not theme_text:
                continue

            matched = any(self._term_matches_text(term, theme_text) for term in normalized_terms)

            if matched:
                filtered.append(item)

        return filtered

    def _build_takeaways(self, report_json: dict, payload: dict, prompt_text: str | None) -> list[str]:
        stats = report_json.get("stats", {})
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)
        total_posts = int(stats.get("total_posts", 0) or 0)
        confidence = payload.get("confidence_assessment", {})
        themes = payload.get("theme_reaction_map", []) or []
        focus_evidence = payload.get("focus_evidence", []) or []
        top_discussed_posts = payload.get("top_discussed_posts", []) or []
        source_comparison = payload.get("source_comparison_map", []) or []
        request = payload.get("analysis_request", {}) or {}
        prompt_modes = set(request.get("prompt_mode", []) or [])
        analysis_axes = set(request.get("analysis_axes", []) or [])
        prompt_focus_terms = request.get("prompt_focus_terms", []) or []
        related_themes = self._filter_prompt_related_themes(themes, focus_evidence, prompt_focus_terms)
        source_only = "source_metrics" in analysis_axes and "post_scope" not in analysis_axes and "comment_reaction" not in analysis_axes
        if request.get("theme_of_posts"):
            top_discussed_posts = payload.get("theme_scoped_posts", []) or []

        takeaways: list[str] = []

        if confidence.get("level") == "low":
            takeaways.append(
                f"Выборка небольшая: {total_posts} постов и {analyzed_comments} релевантных комментариев, поэтому выводы предварительные."
            )

        if ("source_comparison" in prompt_modes or source_only) and source_comparison:
            lead_source = source_comparison[0]
            metric_label = "реакций" if (lead_source.get("platform") or "").lower() == "telegram" else "лайков"
            takeaways.append(
                f"Самая активная аудитория сейчас у источника «{lead_source.get('source_title') or lead_source.get('source_url') or 'без названия'}»: "
                f"{lead_source.get('comments_count', 0)} комментариев, {lead_source.get('likes_count', 0)} {metric_label} и "
                f"{lead_source.get('reposts_count', 0)} репостов по {lead_source.get('posts_count', 0)} постам."
            )
            if len(source_comparison) > 1:
                runner_up = source_comparison[1]
                takeaways.append(
                    f"Ближайший по активности источник — «{runner_up.get('source_title') or runner_up.get('source_url') or 'без названия'}»."
                )
            unique: list[str] = []
            for item in takeaways:
                if item and item not in unique:
                    unique.append(item)
            return unique[:3]

        if focus_evidence and not source_only:
            lead = focus_evidence[0]
            matched_terms = ", ".join(lead.get("matched_terms", [])[:3])
            post = lead.get("post", {})
            post_text = post.get("post_text") or "ключевой публикации"
            if matched_terms:
                takeaways.append(
                    f"Ближе всего к запросу относится сюжет «{post_text}» — он напрямую связан с темами: {matched_terms}."
                )

        if "most_discussed_news" in prompt_modes and top_discussed_posts:
            lead_post = top_discussed_posts[0]
            metric_label = self._engagement_metric_label(lead_post)
            takeaways.append(
                f"Наиболее обсуждаемой выглядит публикация «{lead_post['post_text']}»: {lead_post['comments_count']} комментариев, {lead_post['likes_count']} {metric_label} и {lead_post['reposts_count']} репостов."
            )
        elif related_themes:
            most_interesting = sorted(
                related_themes,
                key=lambda item: (
                    item.get("comments_count", 0),
                    item.get("likes_count", 0),
                    item.get("reposts_count", 0),
                ),
                reverse=True,
            )[0]
            metric_label = self._engagement_metric_label(most_interesting)
            takeaways.append(
                f"Самый сильный отклик вызывает тема «{most_interesting['theme']}»: {most_interesting['comments_count']} комментариев, {most_interesting['likes_count']} {metric_label} и {most_interesting['reposts_count']} репостов."
            )

            strongest_negative = next(
                (item for item in related_themes if item.get("reaction_tendency") == "скорее негативная"),
                None,
            )
            strongest_positive = next(
                (item for item in related_themes if item.get("reaction_tendency") == "скорее позитивная"),
                None,
            )

            if strongest_negative:
                takeaways.append(
                    f"Наиболее негативная реакция заметна вокруг темы «{strongest_negative['theme']}»."
                )
            elif strongest_positive:
                takeaways.append(
                    f"Наиболее позитивная реакция заметна вокруг темы «{strongest_positive['theme']}»."
                )
        elif top_discussed_posts:
            lead_post = top_discussed_posts[0]
            takeaways.append(
                f"Наиболее обсуждаемым оказался пост «{lead_post['post_text']}» с {lead_post['comments_count']} комментариями."
            )

        if not takeaways and prompt_text:
            takeaways.append(f"По запросу «{prompt_text.strip()}» в выборке пока не хватает устойчивых аналитических сигналов.")

        unique: list[str] = []
        for item in takeaways:
            if item and item not in unique:
                unique.append(item)
        return unique[:3]

    def _build_fallback_summary(self, report_json: dict, prompt_text: str | None, payload: dict) -> str:
        stats = report_json.get("stats", {})
        sentiment = report_json.get("sentiment", {})
        request = payload["analysis_request"]
        prompt = request["user_prompt"] or "анализ реакции аудитории"
        modes = set(request["prompt_mode"])
        analysis_axes = set(request.get("analysis_axes", []) or [])
        source_only = "source_metrics" in analysis_axes and "post_scope" not in analysis_axes and "comment_reaction" not in analysis_axes
        declared_theme = request.get("theme_of_posts")

        total_posts = int(stats.get("total_posts", 0) or 0)
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)
        derived_post_themes = payload["derived_post_themes"]
        positive_topics = payload["positive_signals"]["topics"] or payload["positive_signals"]["patterns"]
        negative_topics = payload["negative_signals"]["topics"] or payload["negative_signals"]["patterns"]
        top_discussed_posts = payload["top_discussed_posts"]
        focus_evidence = payload.get("focus_evidence", [])
        theme_reaction_map = payload.get("theme_reaction_map", [])
        source_comparison = payload.get("source_comparison_map", [])

        if analyzed_comments <= 0 and total_posts <= 0:
            return (
                f"По запросу «{prompt}» релевантные комментарии не найдены. "
                "По текущей выборке нельзя сделать содержательный вывод о реакции аудитории."
            )

        parts: list[str] = [f"По запросу «{prompt}» по текущей выборке видна следующая картина. "]

        if ("source_comparison" in modes or source_only) and source_comparison:
            lead = source_comparison[0]
            metric_label = "реакций" if (lead.get("platform") or "").lower() == "telegram" else "лайков"
            parts.append(
                f"Самая активная аудитория в текущей выборке у источника «{lead.get('source_title') or lead.get('source_url') or 'без названия'}»: "
                f"по его постам набирается {lead.get('comments_count', 0)} комментариев, {lead.get('likes_count', 0)} {metric_label} "
                f"и {lead.get('reposts_count', 0)} репостов. "
            )
            if len(source_comparison) > 1:
                runner_up = source_comparison[1]
                parts.append(
                    f"Следом идет источник «{runner_up.get('source_title') or runner_up.get('source_url') or 'без названия'}», "
                    f"поэтому лидерство видно не по одной новости, а по суммарной активности аудитории на уровне канала или сообщества. "
                )

        if not source_only and "most_discussed_news" in modes and top_discussed_posts:
            lead = top_discussed_posts[0]
            metric_label = self._engagement_metric_label(lead)
            parts.append(
                f"Самой обсуждаемой новостью в текущей выборке выглядит публикация «{lead['post_text']}»: "
                f"она собрала {lead['comments_count']} комментариев, {lead['likes_count']} {metric_label}, "
                f"{lead['reposts_count']} репостов. "
            )

        if not source_only and derived_post_themes:
            parts.append(
                f"На уровне самих новостей и постов заметнее всего темы {self._join_list(derived_post_themes[:4])}. "
            )
        elif not source_only and declared_theme:
            parts.append(
                f"Фокус выборки задан темой «{declared_theme}», но при текущем объеме постов устойчивые подтемы автоматически выделяются слабо. "
            )

        if not source_only and "interest_analysis" in modes:
            if focus_evidence:
                lead_focus = focus_evidence[0]["post"]
                parts.append(
                    f"Ближе всего к фокусу запроса оказываются сюжеты вокруг публикации «{lead_focus['post_text']}», "
                    "и именно вокруг них заметнее всего концентрируется обсуждение. "
                )
            elif top_discussed_posts:
                parts.append(
                    f"Наибольший интерес аудитории вызывают сюжеты вокруг публикаций, похожих на «{top_discussed_posts[0]['post_text']}», "
                    "поскольку именно вокруг них сосредоточен основной объем комментариев. "
                )
            elif derived_post_themes:
                parts.append(
                    f"Наибольший интерес аудитории по текущей выборке связан с темами {self._join_list(derived_post_themes[:3])}. "
                )

        if not source_only and "positive_analysis" in modes and positive_topics:
            parts.append(
                f"Скорее позитивно аудитория относится к темам {self._join_list(positive_topics[:3])}. "
            )
        elif not source_only and theme_reaction_map:
            positive_themes = [item["theme"] for item in theme_reaction_map if item.get("reaction_tendency") == "скорее позитивная"]
            if positive_themes:
                parts.append(
                    f"Скорее позитивно аудитория относится к темам {self._join_list(positive_themes[:3])}. "
                )

        if not source_only and "negative_analysis" in modes and negative_topics:
            parts.append(
                f"Негативные эмоции заметнее всего связаны с темами {self._join_list(negative_topics[:3])}. "
            )
        elif not source_only and theme_reaction_map:
            negative_themes = [item["theme"] for item in theme_reaction_map if item.get("reaction_tendency") == "скорее негативная"]
            if negative_themes:
                parts.append(
                    f"Негативные эмоции заметнее всего связаны с темами {self._join_list(negative_themes[:3])}. "
                )

        if not source_only and analyzed_comments > 0:
            parts.append(
                f"Распределение тональности по релевантным комментариям: позитив {sentiment.get('positive_percent', 0)}%, "
                f"негатив {sentiment.get('negative_percent', 0)}%, нейтрально {sentiment.get('neutral_percent', 0)}%. "
            )
        elif not source_only:
            parts.append(
                "Релевантных комментариев по текущему запросу мало или они отсутствуют, поэтому вывод опирается прежде всего на метрики самих постов. "
            )

        if analyzed_comments < 10 or total_posts < 2:
            parts.append(
                f"Данных мало: в анализ попали {total_posts} постов и {analyzed_comments} релевантных комментариев, "
                "поэтому вывод нужно считать предварительным."
            )

        return "".join(parts).strip()

    def _join_list(self, items: list[str]) -> str:
        cleaned = [item for item in items if item]
        if not cleaned:
            return ""
        if len(cleaned) == 1:
            return cleaned[0]
        if len(cleaned) == 2:
            return f"{cleaned[0]} и {cleaned[1]}"
        return ", ".join(cleaned[:-1]) + f" и {cleaned[-1]}"

    def _normalize_text(self, value: str) -> str:
        return " ".join(value.lower().replace("ё", "е").split())

    def _stem_token(self, token: str) -> str:
        normalized = self._normalize_text(token)
        for suffix in RUSSIAN_STEM_SUFFIXES:
            if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 4:
                return normalized[: -len(suffix)]
        return normalized

    def _extract_roots(self, text: str) -> set[str]:
        tokens = re.findall(r"[a-zа-я0-9-]{4,}", self._normalize_text(text))
        roots = {self._stem_token(token) for token in tokens}
        return {root for root in roots if root}

    def _term_matches_text(self, term: str, text: str) -> bool:
        normalized_text = self._normalize_text(text)
        normalized_term = self._normalize_text(term)
        if not normalized_text or not normalized_term:
            return False
        if normalized_term in normalized_text:
            return True

        term_roots = self._extract_roots(normalized_term)
        text_roots = self._extract_roots(normalized_text)
        if not term_roots or not text_roots:
            return False

        for root in term_roots:
            for candidate in text_roots:
                if candidate == root:
                    return True
                if len(root) >= 5 and (candidate.startswith(root) or root.startswith(candidate)):
                    return True
        return False

    def _theme_matches_post(self, theme: str, post: dict) -> bool:
        theme_text = self._normalize_text(theme)
        post_text = self._normalize_text(post.get("post_text") or "")
        if not theme_text or not post_text:
            return False

        for pattern, label in CANONICAL_THEME_PATTERNS:
            if label == theme and re.search(pattern, post_text):
                return True

        tokens = [token for token in re.findall(r"[a-zа-я0-9-]{4,}", theme_text) if token not in POST_THEME_STOPWORDS]
        if not tokens:
            return False
        return all(self._term_matches_text(token, post_text) for token in tokens[:2])

    def _engagement_label(self, comments_count: int, likes_count: int, reposts_count: int) -> str:
        score = comments_count * 5 + likes_count * 2 + reposts_count * 4
        if score >= 150:
            return "высокий"
        if score >= 50:
            return "средний"
        return "низкий"

    def _reaction_label(self, positive_count: int, negative_count: int, neutral_count: int) -> str:
        if positive_count <= 0 and negative_count <= 0:
            return "скорее нейтральная"
        if positive_count >= negative_count * 2 and positive_count > neutral_count * 0.2:
            return "скорее позитивная"
        if negative_count >= positive_count * 2 and negative_count > neutral_count * 0.2:
            return "скорее негативная"
        return "скорее смешанная"

    def _titleize_phrase(self, phrase: str) -> str:
        parts = [part for part in phrase.split() if part]
        if not parts:
            return phrase
        return " ".join(parts).capitalize()

    def _shorten(self, value: str, limit: int = 140) -> str:
        compact = " ".join(value.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3].rstrip() + "..."
