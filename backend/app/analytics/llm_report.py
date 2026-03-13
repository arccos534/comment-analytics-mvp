from __future__ import annotations

import hashlib
import json
import logging

from openai import OpenAI
from redis import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

GENERIC_TOPICS = {"Общее обсуждение", "Общая реакция", "General discussion", "General reaction"}


class SummaryGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)

    def generate_summary_text(self, report_json: dict, prompt_text: str | None = None) -> str:
        analyzed_comments = int(report_json.get("stats", {}).get("analyzed_comments", 0) or 0)
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
                    temperature=0.1,
                    max_tokens=320,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Ты готовишь аналитическую записку по реакции аудитории. "
                                "Тебе переданы: тема и keywords постов, пользовательский prompt для анализа комментариев, "
                                "метрики, значимые темы, сигналы, примеры комментариев и примеры постов. "
                                "Нужно ответить именно на пользовательский prompt, а не пересказывать общую статистику. "
                                "Пиши по-русски, четко, предметно и без воды. "
                                "Если данных мало, прямо скажи, что выводы предварительные. "
                                "Не делай формальный шаблон с обязательными блоками. "
                                "Подзаголовки допустимы только если реально помогают сделать вывод понятнее. "
                                "Не опирайся на generic-темы вроде 'Общее обсуждение' как на смысловой вывод. "
                                "Главный результат должен быть практичным: что вызывает интерес, что вызывает негатив, какие паттерны реакции видны и насколько вывод надежен."
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
        topics = [
            topic
            for topic in (report_json.get("topics", []) or [])
            if (topic.get("name") or "").strip() not in GENERIC_TOPICS
        ][: self.settings.llm_summary_max_topics]
        max_examples = self.settings.llm_summary_max_examples_per_bucket

        return {
            "analysis_request": {
                "post_theme": report_json.get("meta", {}).get("post_theme"),
                "post_keywords": report_json.get("meta", {}).get("post_keywords", []),
                "prompt_for_comment_analysis": prompt_text or "",
                "period_from": report_json.get("meta", {}).get("period_from"),
                "period_to": report_json.get("meta", {}).get("period_to"),
                "platforms": report_json.get("meta", {}).get("platforms", []),
            },
            "coverage": report_json.get("stats", {}),
            "sentiment_distribution": report_json.get("sentiment", {}),
            "meaningful_topics": topics,
            "liked_patterns": report_json.get("insights", {}).get("liked_patterns", []),
            "disliked_patterns": report_json.get("insights", {}).get("disliked_patterns", []),
            "comment_examples": {
                "positive": (examples.get("positive_comments", []) or [])[:max_examples],
                "negative": (examples.get("negative_comments", []) or [])[:max_examples],
                "neutral": (examples.get("neutral_comments", []) or [])[:max_examples],
            },
            "matched_posts": (report_json.get("posts", {}).get("matched", []) or [])[:5],
            "top_popular_posts": (report_json.get("posts", {}).get("top_popular", []) or [])[:3],
            "top_unpopular_posts": (report_json.get("posts", {}).get("top_unpopular", []) or [])[:3],
        }

    def _build_fallback_summary(self, report_json: dict, prompt_text: str | None = None) -> str:
        stats = report_json.get("stats", {})
        sentiment = report_json.get("sentiment", {})
        topics = [
            topic
            for topic in (report_json.get("topics", []) or [])
            if (topic.get("name") or "").strip() not in GENERIC_TOPICS
        ]

        total_posts = int(stats.get("total_posts", 0) or 0)
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)

        if analyzed_comments <= 0:
            return "По выбранной теме и заданному запросу не нашлось достаточного количества релевантных комментариев для уверенного вывода."

        if analyzed_comments < 10 or total_posts < 2:
            return (
                f"По запросу «{(prompt_text or '').strip() or 'анализ реакции аудитории'}» данных пока недостаточно для уверенного вывода: "
                f"в выборке {total_posts} постов и {analyzed_comments} релевантных комментариев. "
                "Стоит расширить период, добавить больше источников или ослабить фильтр темы."
            )

        lead_topic = topics[0]["name"] if topics else None
        topic_part = f" Наиболее содержательные обсуждения связаны с темой «{lead_topic}»." if lead_topic else ""

        return (
            f"По запросу «{(prompt_text or '').strip() or 'анализ реакции аудитории'}» аудитория в основном реагирует нейтрально, "
            f"но заметны различимые сигналы интереса и негатива: позитив {sentiment.get('positive_percent', 0)}%, "
            f"негатив {sentiment.get('negative_percent', 0)}%, нейтрально {sentiment.get('neutral_percent', 0)}%."
            f"{topic_part} Для более точного вывода стоит опираться на больший объем релевантных комментариев и примеров постов."
        )
