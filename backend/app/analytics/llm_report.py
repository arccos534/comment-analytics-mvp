from __future__ import annotations

import hashlib
import json
import logging

from openai import OpenAI
from redis import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class SummaryGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)

    def generate_summary_text(self, report_json: dict, prompt_text: str | None = None) -> str:
        analyzed_comments = report_json.get("stats", {}).get("analyzed_comments", 0)
        llm_enabled = (
            self.settings.llm_summary_enabled
            and self.settings.openai_compatible_base_url
            and self.settings.openai_compatible_api_key
            and analyzed_comments >= self.settings.llm_summary_min_comments
        )

        if llm_enabled:
            try:
                summary_payload = self._build_summary_payload(report_json, prompt_text)
                cache_key = self._build_cache_key(summary_payload)
                cached = self.redis.get(cache_key)
                if cached:
                    return cached

                client = OpenAI(
                    base_url=self.settings.openai_compatible_base_url,
                    api_key=self.settings.openai_compatible_api_key,
                )
                completion = client.chat.completions.create(
                    model=self.settings.openai_compatible_model,
                    temperature=0,
                    max_tokens=260,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Ты аналитик пользовательской реакции. "
                                "Ответь на запрос пользователя одним четким, полезным и деловым текстом на русском языке. "
                                "Не используй фиксированный шаблон и не выдумывай обязательные блоки. "
                                "Если подзаголовки действительно помогают, добавь их сам, но только при необходимости. "
                                "Главное: прямо ответь на prompt, опирайся только на данные отчета, отмечай ограничения выборки только если они реально мешают уверенным выводам. "
                                "Избегай воды, общих фраз и повторения цифр без смысла."
                            ),
                        },
                        {
                            "role": "user",
                            "content": json.dumps(summary_payload, ensure_ascii=False),
                        },
                    ],
                )
                content = (completion.choices[0].message.content or "").strip()
                if content:
                    self.redis.setex(cache_key, self.settings.llm_summary_cache_ttl_seconds, content)
                    return content
            except Exception:
                logger.exception("LLM summary generation failed")

        return self._build_fallback_summary(report_json, prompt_text)

    def _build_cache_key(self, summary_payload: dict) -> str:
        digest = hashlib.sha256(
            json.dumps(summary_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        return f"summary-cache:{self.settings.openai_compatible_model}:{digest}"

    def _build_summary_payload(self, report_json: dict, prompt_text: str | None) -> dict:
        examples = report_json.get("examples", {})
        max_examples = self.settings.llm_summary_max_examples_per_bucket
        return {
            "prompt_text": prompt_text or "",
            "meta": report_json.get("meta", {}),
            "stats": report_json.get("stats", {}),
            "sentiment": report_json.get("sentiment", {}),
            "topics": (report_json.get("topics", []) or [])[: self.settings.llm_summary_max_topics],
            "insights": report_json.get("insights", {}),
            "examples": {
                "positive_comments": (examples.get("positive_comments", []) or [])[:max_examples],
                "negative_comments": (examples.get("negative_comments", []) or [])[:max_examples],
                "neutral_comments": (examples.get("neutral_comments", []) or [])[:max_examples],
            },
            "posts": {
                "matched": (report_json.get("posts", {}).get("matched", []) or [])[:3],
                "top_popular": (report_json.get("posts", {}).get("top_popular", []) or [])[:3],
                "top_unpopular": (report_json.get("posts", {}).get("top_unpopular", []) or [])[:3],
            },
        }

    def _build_fallback_summary(self, report_json: dict, prompt_text: str | None = None) -> str:
        stats = report_json.get("stats", {})
        sentiment = report_json.get("sentiment", {})
        topics = report_json.get("topics", [])

        total_posts = int(stats.get("total_posts", 0) or 0)
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)
        lead_topic = topics[0]["name"] if topics else "общая реакция"

        if analyzed_comments <= 0:
            return "По выбранной теме и заданному запросу не нашлось достаточного количества релевантных комментариев для уверенного вывода."

        limitations = ""
        if total_posts < 3 or analyzed_comments < 20:
            limitations = " Выборка небольшая, поэтому выводы стоит считать предварительными."

        prompt_part = f"По запросу «{prompt_text.strip()}» " if prompt_text and prompt_text.strip() else ""
        return (
            f"{prompt_part}основной массив обсуждений связан с темой «{lead_topic}». "
            f"Распределение тональности выглядит так: позитив {sentiment.get('positive_percent', 0)}%, "
            f"негатив {sentiment.get('negative_percent', 0)}%, нейтрально {sentiment.get('neutral_percent', 0)}%."
            f"{limitations}"
        )
