from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter

from openai import OpenAI
from redis import Redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

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
    "который",
    "которая",
    "которые",
    "которых",
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
    "того",
    "тогда",
    "потом",
    "лишь",
    "если",
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
                    temperature=0,
                    max_tokens=320,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Ты готовишь прикладную аналитическую записку по реакции аудитории на новости и посты. "
                                "Твоя главная задача — ответить именно на пользовательский запрос, а не пересказывать сырые поля отчета. "
                                "Сначала определи 2-5 конкретных тем новостей/постов по полям post_theme_candidates, matched_posts, "
                                "top_popular_posts и top_unpopular_posts. Затем объясни, какие темы вызвали интерес, какие — негатив, "
                                "и какие паттерны реакции видны в комментариях. "
                                "Нельзя использовать generic-формулировки вроде 'Общее обсуждение' как основной вывод. "
                                "Нельзя строить ответ вокруг процентов без интерпретации смысла. "
                                "Если данных мало или вывод ненадежен, скажи это прямо и коротко. "
                                "Пиши по-русски, предметно, ясно и без воды. Верни один цельный, хорошо структурированный аналитический текст, "
                                "который можно показать заказчику как итог по заданному prompt."
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
        posts = report_json.get("posts", {})
        matched_posts = (posts.get("matched", []) or [])[:8]
        top_popular = (posts.get("top_popular", []) or [])[:5]
        top_unpopular = (posts.get("top_unpopular", []) or [])[:5]
        max_examples = self.settings.llm_summary_max_examples_per_bucket

        meaningful_topics = [
            topic
            for topic in (report_json.get("topics", []) or [])
            if (topic.get("name") or "").strip() not in GENERIC_TOPICS
        ][: self.settings.llm_summary_max_topics]

        post_theme_candidates = self._extract_post_theme_candidates(matched_posts + top_popular + top_unpopular)

        return {
            "analysis_request": {
                "theme_of_posts": report_json.get("meta", {}).get("post_theme"),
                "keywords_for_posts": report_json.get("meta", {}).get("post_keywords", []),
                "prompt_for_comment_analysis": (prompt_text or "").strip(),
                "period_from": report_json.get("meta", {}).get("period_from"),
                "period_to": report_json.get("meta", {}).get("period_to"),
                "platforms": report_json.get("meta", {}).get("platforms", []),
            },
            "coverage": report_json.get("stats", {}),
            "sentiment_distribution": report_json.get("sentiment", {}),
            "meaningful_comment_topics": meaningful_topics,
            "post_theme_candidates": post_theme_candidates,
            "liked_patterns": report_json.get("insights", {}).get("liked_patterns", []),
            "disliked_patterns": report_json.get("insights", {}).get("disliked_patterns", []),
            "comment_examples": {
                "positive": (examples.get("positive_comments", []) or [])[:max_examples],
                "negative": (examples.get("negative_comments", []) or [])[:max_examples],
                "neutral": (examples.get("neutral_comments", []) or [])[:max_examples],
            },
            "matched_posts": [self._compact_post(post) for post in matched_posts],
            "top_popular_posts": [self._compact_post(post) for post in top_popular],
            "top_unpopular_posts": [self._compact_post(post) for post in top_unpopular],
        }

    def _extract_post_theme_candidates(self, posts: list[dict]) -> list[str]:
        unigram_counter: Counter[str] = Counter()
        bigram_counter: Counter[str] = Counter()

        for post in posts:
            text = self._normalize_text(post.get("post_text") or "")
            tokens = [token for token in re.findall(r"[a-zа-я0-9-]{3,}", text) if not token.isdigit()]
            filtered = [token for token in tokens if token not in POST_THEME_STOPWORDS]

            for token in filtered:
                unigram_counter[token] += 1

            for left, right in zip(filtered, filtered[1:]):
                if left == right:
                    continue
                bigram_counter[f"{left} {right}"] += 1

        themes: list[str] = []
        for phrase, count in bigram_counter.most_common(12):
            if count < 2:
                continue
            if any(part in POST_THEME_STOPWORDS for part in phrase.split()):
                continue
            themes.append(self._titleize_phrase(phrase))
            if len(themes) >= 5:
                break

        if len(themes) < 5:
            for token, count in unigram_counter.most_common(20):
                if count < 2:
                    continue
                title = self._titleize_phrase(token)
                if title not in themes:
                    themes.append(title)
                if len(themes) >= 8:
                    break

        return themes[:8]

    def _compact_post(self, post: dict) -> dict:
        return {
            "post_text": self._shorten(post.get("post_text") or "", limit=220),
            "score": post.get("score", 0),
            "comments_count": post.get("comments_count", 0),
        }

    def _build_fallback_summary(self, report_json: dict, prompt_text: str | None = None) -> str:
        stats = report_json.get("stats", {})
        sentiment = report_json.get("sentiment", {})
        posts = (report_json.get("posts", {}).get("matched", []) or [])[:8]
        post_topics = self._extract_post_theme_candidates(posts)
        prompt = (prompt_text or "").strip() or "анализ реакции аудитории"

        total_posts = int(stats.get("total_posts", 0) or 0)
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)

        if analyzed_comments <= 0:
            return (
                f"По запросу «{prompt}» релевантные комментарии не найдены. "
                "По текущей выборке нельзя сделать содержательный вывод о реакции аудитории."
            )

        if analyzed_comments < 10 or total_posts < 2:
            return (
                f"По запросу «{prompt}» данных пока недостаточно для уверенного вывода: "
                f"в анализ попали {total_posts} постов и {analyzed_comments} релевантных комментариев. "
                "Сейчас можно зафиксировать только предварительный сигнал, но не устойчивую картину реакции аудитории."
            )

        topic_sentence = ""
        if post_topics:
            topic_sentence = (
                f"Наиболее заметные темы самих новостей и постов в текущей выборке: {', '.join(post_topics[:4])}. "
            )

        return (
            f"По запросу «{prompt}» в выборке просматривается следующая картина. "
            f"{topic_sentence}"
            f"Комментарийная реакция в основном нейтральная, но внутри обсуждений есть различимые сигналы интереса и негатива: "
            f"позитив {sentiment.get('positive_percent', 0)}%, негатив {sentiment.get('negative_percent', 0)}%, "
            f"нейтрально {sentiment.get('neutral_percent', 0)}%. "
            "Для сильного аналитического вывода стоит опираться на более широкий объем релевантных комментариев и большее число постов, "
            "но уже сейчас можно анализировать не абстрактное «общее обсуждение», а конкретные темы самих новостей."
        )

    def _normalize_text(self, value: str) -> str:
        return " ".join(value.lower().replace("ё", "е").split())

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
