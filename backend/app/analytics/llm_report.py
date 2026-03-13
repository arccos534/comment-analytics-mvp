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
                                "Нужно ответить именно на пользовательский запрос, а не пересказать поля отчета. "
                                "Опирайся прежде всего на темы самих новостей и постов: post_theme_candidates, matched_posts, "
                                "top_popular_posts и top_unpopular_posts. Темы комментариев используй только как дополнительный контекст. "
                                "В итоговом тексте обязательно прямо ответь на четыре вопроса, даже если ответ по некоторым пунктам осторожный: "
                                "1) какие новости или темы вызвали наибольший интерес аудитории; "
                                "2) какие новости или темы вызвали негативные эмоции; "
                                "3) к каким темам аудитория отнеслась скорее позитивно; "
                                "4) к каким темам аудитория отнеслась скорее негативно. "
                                "Нельзя использовать generic-формулировки вроде 'Общее обсуждение' как главный вывод. "
                                "Нельзя ограничиваться процентами без объяснения, о каких темах идет речь. "
                                "Если данных мало, скажи это прямо, но все равно дай максимально конкретный предварительный вывод по имеющимся данным. "
                                "Пиши по-русски, предметно, короткими абзацами, без воды. Разрешены естественные подзаголовки, если они помогают читаемости."
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
        posts = report_json.get("posts", {})
        matched_posts = (posts.get("matched", []) or [])[:8]
        popular_posts = (posts.get("top_popular", []) or [])[:5]
        unpopular_posts = (posts.get("top_unpopular", []) or [])[:5]

        post_topics = self._extract_post_theme_candidates(matched_posts)
        interest_topics = self._extract_post_theme_candidates(popular_posts) or post_topics
        low_engagement_topics = self._extract_post_theme_candidates(unpopular_posts)

        liked_patterns = report_json.get("insights", {}).get("liked_patterns", []) or []
        disliked_patterns = report_json.get("insights", {}).get("disliked_patterns", []) or []
        positive_topics = self._extract_meaningful_comment_topics(report_json, positive=True)
        negative_topics = self._extract_meaningful_comment_topics(report_json, positive=False)

        prompt = (prompt_text or "").strip() or "анализ реакции аудитории"

        total_posts = int(stats.get("total_posts", 0) or 0)
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)

        if analyzed_comments <= 0:
            return (
                f"По запросу «{prompt}» релевантные комментарии не найдены. "
                "По текущей выборке нельзя сделать содержательный вывод о реакции аудитории."
            )

        if analyzed_comments < 10 or total_posts < 2:
            concise_interest = self._join_list(interest_topics[:3]) or "выраженные темы интереса пока не выделяются"
            concise_negative = self._join_list(negative_topics[:3] or disliked_patterns[:3]) or "устойчивые негативные темы пока не выделяются"
            return (
                f"По запросу «{prompt}» данных пока недостаточно для уверенного вывода: "
                f"в анализ попали {total_posts} постов и {analyzed_comments} релевантных комментариев. "
                f"Предварительно можно сказать, что интерес аудитории чаще возникает вокруг тем: {concise_interest}. "
                f"Негативные сигналы пока заметнее всего связаны с темами: {concise_negative}. "
                "Этот вывод нужно считать предварительным, а не устойчивым."
            )

        overview_line = ""
        if post_topics:
            overview_line = f"В текущей выборке заметнее всего темы самих новостей и постов: {self._join_list(post_topics[:4])}. "

        interest_line = (
            f"Наибольший интерес аудитории вызывают новости и посты на темы {self._join_list(interest_topics[:4])}. "
            if interest_topics
            else "Наиболее сильный интерес аудитории по текущей выборке не выделяется достаточно уверенно. "
        )

        negative_emotion_basis = negative_topics[:4] or disliked_patterns[:4] or low_engagement_topics[:4]
        negative_line = (
            f"Негативные эмоции чаще возникают вокруг тем {self._join_list(negative_emotion_basis)}. "
            if negative_emotion_basis
            else "Явно выраженные темы, которые стабильно вызывают негативные эмоции, по текущей выборке не выделяются. "
        )

        positive_basis = positive_topics[:4] or liked_patterns[:4] or interest_topics[:4]
        positive_line = (
            f"Скорее позитивно аудитория относится к темам {self._join_list(positive_basis)}. "
            if positive_basis
            else "Стабильные позитивные темы по текущей выборке выражены слабо. "
        )

        negative_attitude_basis = negative_topics[:4] or disliked_patterns[:4]
        attitude_line = (
            f"Скорее негативно аудитория относится к темам {self._join_list(negative_attitude_basis)}. "
            if negative_attitude_basis
            else "Устойчивой группы тем с явно отрицательным отношением аудитории по текущей выборке не видно. "
        )

        return (
            f"По запросу «{prompt}» картина по текущей выборке выглядит так. "
            f"{overview_line}"
            f"{interest_line}"
            f"{negative_line}"
            f"{positive_line}"
            f"{attitude_line}"
            f"Распределение тональности по релевантным комментариям: позитив {sentiment.get('positive_percent', 0)}%, "
            f"негатив {sentiment.get('negative_percent', 0)}%, нейтрально {sentiment.get('neutral_percent', 0)}%. "
            "Если нужен более надежный вывод, стоит расширить выборку постов и релевантных комментариев."
        )

    def _extract_meaningful_comment_topics(self, report_json: dict, positive: bool) -> list[str]:
        examples_key = "positive_comments" if positive else "negative_comments"
        examples = report_json.get("examples", {}).get(examples_key, []) or []
        fallback_topics = [
            (topic.get("name") or "").strip()
            for topic in (report_json.get("topics", []) or [])
            if (topic.get("name") or "").strip() and (topic.get("name") or "").strip() not in GENERIC_TOPICS
        ]

        counter: Counter[str] = Counter()
        for example in examples:
            text = self._normalize_text(example.get("text") or "")
            tokens = [token for token in re.findall(r"[a-zа-я0-9-]{4,}", text) if token not in POST_THEME_STOPWORDS]
            for token in tokens:
                counter[token] += 1

        extracted = [self._titleize_phrase(token) for token, count in counter.most_common(6) if count >= 1]
        ordered = []
        for topic in extracted + fallback_topics:
            if topic and topic not in ordered:
                ordered.append(topic)
        return ordered[:6]

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
