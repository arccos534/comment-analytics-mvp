from __future__ import annotations

import hashlib
import json
import logging
import re
from collections.abc import Iterable

from app.analytics.keywords import KeywordExtractor
from app.analytics.sentiment import SentimentAnalyzer
from app.analytics.topics import TopicGrouper
from app.core.config import get_settings
from app.models.enums import SentimentEnum

try:
    from redis import Redis
except Exception:  # pragma: no cover
    Redis = None

try:
    from openai import OpenAI
except Exception:  # pragma: no cover
    OpenAI = None

logger = logging.getLogger(__name__)

COMMENT_ANALYSIS_CACHE_VERSION = "v2"
COMMENT_ANALYSIS_PROMPT_VERSION = "comment-analysis-v2"

GENERIC_TOPIC_PHRASES = {
    "общее обсуждение",
    "общая реакция",
    "мнение людей",
    "комментарий к новости",
    "отношение к новости",
    "реакция аудитории",
}

GENERIC_KEYWORD_PHRASES = {
    "новость",
    "пост",
    "комментарий",
    "люди",
    "аудитория",
    "реакция",
}


class LLMCommentAnalyzer:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True) if Redis else None
        self.sentiment_fallback = SentimentAnalyzer()
        self.keyword_fallback = KeywordExtractor()
        self.topic_fallback = TopicGrouper()

    def analyze_many(self, items: list[dict]) -> list[dict]:
        if not items:
            return []

        results: list[dict | None] = [None] * len(items)
        unresolved: list[tuple[int, dict]] = []

        for index, item in enumerate(items):
            cached = self._get_cached_result(item)
            if cached:
                results[index] = cached
            else:
                unresolved.append((index, item))

        if self._llm_enabled() and unresolved:
            batch_size = max(int(self.settings.llm_comment_analysis_batch_size or 10), 1)
            for start in range(0, len(unresolved), batch_size):
                batch = unresolved[start:start + batch_size]
                batch_results = self._analyze_batch_with_llm(batch)
                for index, result in batch_results.items():
                    results[index] = result

        for index, item in enumerate(items):
            if results[index] is None:
                results[index] = self._fallback_analysis(item)

        return [
            result if result is not None else self._fallback_analysis(items[index])
            for index, result in enumerate(results)
        ]

    def _llm_enabled(self) -> bool:
        return bool(
            OpenAI
            and self.settings.llm_comment_analysis_enabled
            and self.settings.openai_compatible_base_url
            and self.settings.openai_compatible_api_key
        )

    def _analyze_batch_with_llm(self, batch: list[tuple[int, dict]]) -> dict[int, dict]:
        payload = {
            "items": [
                {
                    "index": index,
                    "post_context": self._prepare_post_context(item.get("post_text") or ""),
                    "comment_text": self._prepare_comment_text(item.get("comment_text") or ""),
                }
                for index, item in batch
            ]
        }

        try:
            client = OpenAI(
                base_url=self.settings.openai_compatible_base_url,
                api_key=self.settings.openai_compatible_api_key,
            )
            completion = client.chat.completions.create(
                model=self._comment_model(),
                max_completion_tokens=max(int(self.settings.llm_comment_analysis_max_completion_tokens or 700), 200),
                messages=[
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                **self._completion_options(),
            )
            self._log_openai_completion(completion, "comment_analysis")
            content = self._extract_json_text((completion.choices[0].message.content or "").strip())
            parsed = json.loads(content)
            response_items = parsed.get("items") if isinstance(parsed, dict) else None
            if not isinstance(response_items, list):
                raise ValueError("comment analysis response has no items list")
        except Exception:
            logger.exception("LLM comment analysis failed for batch")
            return {index: self._fallback_analysis(item) for index, item in batch}

        input_map = {index: item for index, item in batch}
        resolved: dict[int, dict] = {}
        for raw_item in response_items:
            if not isinstance(raw_item, dict):
                continue
            try:
                index = int(raw_item.get("index"))
            except (TypeError, ValueError):
                continue
            source = input_map.get(index)
            if not source:
                continue
            normalized = self._normalize_llm_result(raw_item, source)
            resolved[index] = normalized
            self._cache_result(source, normalized)

        for index, item in batch:
            if index not in resolved:
                resolved[index] = self._fallback_analysis(item)
        return resolved

    def _normalize_llm_result(self, raw_item: dict, source: dict) -> dict:
        sentiment_value = str(raw_item.get("sentiment") or "").strip().lower()
        if sentiment_value not in {member.value for member in SentimentEnum}:
            return self._fallback_analysis(source)

        try:
            score = float(raw_item.get("score", 0.0) or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        score = max(-1.0, min(1.0, score))

        topics = self._clean_phrases(
            raw_item.get("topics"),
            limit=2,
            titleize=True,
            generic=GENERIC_TOPIC_PHRASES,
        )
        keywords = self._clean_phrases(
            raw_item.get("keywords"),
            limit=3,
            titleize=False,
            generic=GENERIC_KEYWORD_PHRASES,
        )

        if not topics:
            fallback = self._fallback_analysis(source)
            topics = fallback["topics"]
        if not keywords:
            fallback = self._fallback_analysis(source)
            keywords = fallback["keywords"]

        return {
            "sentiment": sentiment_value,
            "score": score,
            "topics": topics,
            "keywords": keywords,
        }

    def _fallback_analysis(self, item: dict) -> dict:
        comment_text = item.get("comment_text") or ""
        sentiment_result = self.sentiment_fallback.analyze(comment_text)
        keywords = self.keyword_fallback.extract(comment_text)
        topics = self.topic_fallback.group(keywords, comment_text)
        return {
            "sentiment": sentiment_result["sentiment"].value,
            "score": float(sentiment_result["score"] or 0.0),
            "topics": topics,
            "keywords": keywords,
        }

    def _cache_key(self, item: dict) -> str:
        raw = json.dumps(
            {
                "comment_text": self._prepare_comment_text(item.get("comment_text") or ""),
                "post_context": self._prepare_post_context(item.get("post_text") or ""),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return (
            f"comment-analysis-cache:{COMMENT_ANALYSIS_CACHE_VERSION}:{COMMENT_ANALYSIS_PROMPT_VERSION}:"
            f"{self._comment_model()}:{self._comment_reasoning_effort() or 'none'}:{digest}"
        )

    def _get_cached_result(self, item: dict) -> dict | None:
        if not self._llm_enabled() or not self.redis:
            return None
        cached = self.redis.get(self._cache_key(item))
        if not cached:
            return None
        try:
            parsed = json.loads(cached)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        return self._normalize_llm_result(parsed, item)

    def _cache_result(self, item: dict, result: dict) -> None:
        if not self._llm_enabled() or not self.redis:
            return
        ttl = max(int(self.settings.llm_comment_analysis_cache_ttl_seconds or 0), 60)
        self.redis.setex(self._cache_key(item), ttl, json.dumps(result, ensure_ascii=False))

    def _build_system_prompt(self) -> str:
        return (
            "Analyze Russian social-media comments in the context of the post they reply to.\n"
            "Return strict JSON object with one key: items.\n"
            "For each input item return:\n"
            '- index: integer from the input\n'
            '- sentiment: "positive" | "negative" | "neutral"\n'
            "- score: float from -1.0 to 1.0\n"
            "- topics: 1-2 short Russian motive labels, not generic and not broken fragments\n"
            "- keywords: 1-3 short Russian signal phrases, not generic filler\n"
            "Rules:\n"
            "- Negative means criticism, distrust, accusation, disappointment, anger, complaint, fear, or mention of fake, fraud, poor quality.\n"
            "- Positive means approval, praise, support, gratitude, relief, or clear agreement.\n"
            "- Neutral means factual, mixed, unclear, weak emotion, or off-topic.\n"
            "- Use post_context to resolve short comments.\n"
            "- Keep the JSON compact and do not add explanations outside JSON.\n"
        )

    def _prepare_post_context(self, text: str) -> str:
        prepared = re.sub(r"https?://\S+|t\.me/\S+|vk\.com/\S+", " ", text)
        prepared = re.sub(r"\s+", " ", prepared).strip()
        return prepared[:160]

    def _prepare_comment_text(self, text: str) -> str:
        prepared = re.sub(r"\s+", " ", text).strip()
        return prepared[:280]

    def _extract_json_text(self, text: str) -> str:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        return cleaned

    def _clean_phrases(
        self,
        values: object,
        limit: int,
        titleize: bool,
        generic: set[str],
    ) -> list[str]:
        phrases: list[str] = []
        if isinstance(values, str):
            raw_values: Iterable[str] = [values]
        elif isinstance(values, list):
            raw_values = [str(item) for item in values if isinstance(item, (str, int, float))]
        else:
            raw_values = []

        for raw in raw_values:
            cleaned = re.sub(r"\s+", " ", str(raw)).strip(" .,!?:;\"'()[]{}")
            if not cleaned:
                continue
            normalized = cleaned.lower()
            if normalized in generic:
                continue
            if len(normalized) < 3:
                continue
            if titleize:
                cleaned = cleaned[0].upper() + cleaned[1:]
            if cleaned not in phrases:
                phrases.append(cleaned)
            if len(phrases) >= limit:
                break
        return phrases

    def _completion_options(self) -> dict:
        effort = self._comment_reasoning_effort()
        if effort and effort != "none":
            return {"reasoning_effort": effort}
        return {}

    def _comment_model(self) -> str:
        return (
            (self.settings.openai_comment_analysis_model or "").strip()
            or self.settings.openai_compatible_model
        )

    def _comment_reasoning_effort(self) -> str:
        return (
            (self.settings.openai_comment_analysis_reasoning_effort or "").strip().lower()
            or "none"
        )

    def _log_openai_completion(self, completion, purpose: str) -> None:
        usage = getattr(completion, "usage", None)
        logger.info(
            "OpenAI completion succeeded",
            extra={
                "purpose": purpose,
                "requested_model": self._comment_model(),
                "response_model": getattr(completion, "model", None),
                "reasoning_effort": self._comment_reasoning_effort(),
                "prompt_tokens": getattr(usage, "prompt_tokens", None),
                "completion_tokens": getattr(usage, "completion_tokens", None),
                "total_tokens": getattr(usage, "total_tokens", None),
            },
        )
