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
    "тогда",
    "потом",
    "лишь",
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


class SummaryGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis = Redis.from_url(self.settings.redis_url, decode_responses=True)

    def generate_summary_text(self, report_json: dict, prompt_text: str | None = None) -> str:
        analyzed_comments = int(report_json.get("stats", {}).get("analyzed_comments", 0) or 0)
        summary_payload = self._build_summary_payload(report_json, prompt_text)
        llm_enabled = (
            self.settings.llm_summary_enabled
            and self.settings.openai_compatible_base_url
            and self.settings.openai_compatible_api_key
            and analyzed_comments >= self.settings.llm_summary_min_comments
        )

        if llm_enabled:
            try:
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
                    max_completion_tokens=360,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Ты готовишь финальную аналитическую записку по реакции аудитории на новости и посты. "
                                "Твоя задача — максимально точно ответить на пользовательский запрос, а не пересказывать поля отчета. "
                                "Сначала определи, что именно требуется по полям user_prompt и request_contract. "
                                "Затем дай конкретный аналитический вывод по этим пунктам, используя прежде всего темы самих постов и новостей, "
                                "а комментарии — как подтверждающий слой. "
                                "Используй только темы, которые реально подтверждаются полями derived_post_themes, matched_posts, top_popular_posts и top_unpopular_posts. "
                                "Не подменяй конкретные темы словами вроде 'Общее обсуждение'. "
                                "Не ограничивайся процентами без объяснения, какие темы и сюжеты стоят за цифрами. "
                                "Если данных мало, прямо скажи об ограничениях, но все равно дай максимально конкретный предварительный вывод. "
                                "Пиши по-русски, предметно, без воды. Верни один связный, хорошо структурированный аналитический текст, подходящий для заказчика. "
                                "Подзаголовки допустимы только если они реально улучшают ответ."
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

        return self._build_fallback_summary(report_json, prompt_text, summary_payload)

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
        max_examples = max(self.settings.llm_summary_max_examples_per_bucket, 2)

        meaningful_topics = [
            topic
            for topic in (report_json.get("topics", []) or [])
            if (topic.get("name") or "").strip() not in GENERIC_TOPICS
        ][: self.settings.llm_summary_max_topics]

        derived_post_themes = self._extract_post_theme_candidates(matched_posts + top_popular + top_unpopular)

        return {
            "analysis_request": {
                "theme_of_posts": (report_json.get("meta", {}).get("post_theme") or "").strip() or None,
                "keywords_for_posts": report_json.get("meta", {}).get("post_keywords", []),
                "user_prompt": (prompt_text or "").strip(),
                "request_contract": self._infer_request_contract(prompt_text),
                "period_from": report_json.get("meta", {}).get("period_from"),
                "period_to": report_json.get("meta", {}).get("period_to"),
                "platforms": report_json.get("meta", {}).get("platforms", []),
            },
            "coverage": report_json.get("stats", {}),
            "sentiment_distribution": report_json.get("sentiment", {}),
            "derived_post_themes": derived_post_themes,
            "comment_topics": meaningful_topics,
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
            "top_popular_posts": [self._compact_post(post) for post in top_popular],
            "top_unpopular_posts": [self._compact_post(post) for post in top_unpopular],
        }

    def _infer_request_contract(self, prompt_text: str | None) -> list[str]:
        prompt = self._normalize_text(prompt_text or "")
        if not prompt:
            return ["Дай конкретный аналитический вывод по реакции аудитории на выбранные посты."]

        contract: list[str] = []
        patterns = [
            (r"интерес|интересуют|интересны|вовлеч", "Определи, какие новости и темы вызывают наибольший интерес аудитории."),
            (r"негатив|негативн|эмоц|раздраж|крити|возмущ", "Определи, какие новости и темы вызывают негативные эмоции аудитории."),
            (r"позитив|нравит|положит", "Определи, к каким темам аудитория относится скорее позитивно."),
            (r"не нрав|отрицат|претенз|жалоб|проблем", "Определи, к каким темам аудитория относится скорее негативно."),
            (r"тем|сюжет|новост", "Выдели конкретные темы самих новостей и постов, реально видимые в выборке."),
            (r"сравн|разниц|отлич", "Сравни реакции аудитории между основными темами."),
            (r"почему|причин", "Объясни, почему аудитория реагирует именно так, опираясь на комментарии и примеры постов."),
        ]

        for pattern, instruction in patterns:
            if re.search(pattern, prompt):
                contract.append(instruction)

        if not contract:
            contract.append("Дай конкретный аналитический ответ на запрос пользователя, опираясь на темы постов и реакцию аудитории.")

        return contract

    def _extract_post_theme_candidates(self, posts: list[dict]) -> list[str]:
        if len(posts) < 2:
            return []

        unigram_counter: Counter[str] = Counter()
        bigram_counter: Counter[str] = Counter()

        for post in posts:
            text = self._normalize_text(post.get("post_text") or "")
            tokens = [token for token in re.findall(r"[a-zа-я0-9-]{3,}", text) if not token.isdigit()]
            filtered = [token for token in tokens if token not in POST_THEME_STOPWORDS]

            unique_tokens = list(dict.fromkeys(filtered))
            for token in unique_tokens:
                unigram_counter[token] += 1

            seen_bigrams: set[str] = set()
            for left, right in zip(filtered, filtered[1:]):
                if left == right:
                    continue
                phrase = f"{left} {right}"
                if phrase in seen_bigrams:
                    continue
                seen_bigrams.add(phrase)
                bigram_counter[phrase] += 1

        themes: list[str] = []
        for phrase, count in bigram_counter.most_common(16):
            if count < 2:
                continue
            if any(part in POST_THEME_STOPWORDS for part in phrase.split()):
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

        return themes[:8]

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
            "post_text": self._shorten(post.get("post_text") or "", limit=220),
            "score": post.get("score", 0),
            "comments_count": post.get("comments_count", 0),
        }

    def _build_fallback_summary(self, report_json: dict, prompt_text: str | None, payload: dict) -> str:
        stats = report_json.get("stats", {})
        sentiment = report_json.get("sentiment", {})
        request = payload["analysis_request"]
        prompt = request["user_prompt"] or "анализ реакции аудитории"
        contract = request["request_contract"]
        declared_theme = request.get("theme_of_posts")

        total_posts = int(stats.get("total_posts", 0) or 0)
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)
        derived_post_themes = payload["derived_post_themes"]
        positive_topics = payload["positive_signals"]["topics"] or payload["positive_signals"]["patterns"]
        negative_topics = payload["negative_signals"]["topics"] or payload["negative_signals"]["patterns"]

        if analyzed_comments <= 0:
            return (
                f"По запросу «{prompt}» релевантные комментарии не найдены. "
                "По текущей выборке нельзя сделать содержательный вывод о реакции аудитории."
            )

        parts: list[str] = [f"По запросу «{prompt}» картина по текущей выборке выглядит так. "]

        if derived_post_themes:
            parts.append(f"На уровне самих новостей и постов наиболее заметны темы {self._join_list(derived_post_themes[:4])}. ")
        elif declared_theme:
            parts.append(f"Фокус выборки задан темой «{declared_theme}», но при текущем объеме постов устойчивые подтемы автоматически выделяются слабо. ")

        normalized_prompt = self._normalize_text(prompt)
        if self._request_mentions_interest(contract, normalized_prompt):
            if derived_post_themes:
                parts.append(f"Наибольший интерес аудитории по текущей выборке чаще связан с темами {self._join_list(derived_post_themes[:3])}. ")
            else:
                parts.append("Темы, стабильно вызывающие наибольший интерес аудитории, по текущей выборке выделяются неуверенно. ")

        if self._request_mentions_negative_emotions(contract, normalized_prompt):
            if negative_topics:
                parts.append(f"Негативные эмоции заметнее всего связаны с темами {self._join_list(negative_topics[:3])}. ")
            else:
                parts.append("Устойчивые темы, явно вызывающие негативные эмоции, по текущей выборке не выделяются. ")

        if self._request_mentions_positive_attitude(contract, normalized_prompt):
            if positive_topics:
                parts.append(f"Скорее позитивно аудитория относится к темам {self._join_list(positive_topics[:3])}. ")
            else:
                parts.append("Стабильные темы с выраженно позитивной реакцией аудитории по текущей выборке видны слабо. ")

        if self._request_mentions_negative_attitude(contract, normalized_prompt):
            if negative_topics:
                parts.append(f"Скорее негативно аудитория относится к темам {self._join_list(negative_topics[:3])}. ")
            else:
                parts.append("Устойчивой группы тем с явно отрицательным отношением аудитории по текущей выборке не видно. ")

        parts.append(
            f"Распределение тональности по релевантным комментариям: позитив {sentiment.get('positive_percent', 0)}%, "
            f"негатив {sentiment.get('negative_percent', 0)}%, нейтрально {sentiment.get('neutral_percent', 0)}%. "
        )

        if analyzed_comments < 10 or total_posts < 2:
            parts.append(
                f"Данных мало: в анализ попали {total_posts} постов и {analyzed_comments} релевантных комментариев, "
                "поэтому вывод нужно считать предварительным."
            )

        return "".join(parts).strip()

    def _request_mentions_interest(self, contract: list[str], prompt: str) -> bool:
        return any("интерес" in item.lower() for item in contract) or bool(re.search(r"интерес|вовлеч", prompt))

    def _request_mentions_negative_emotions(self, contract: list[str], prompt: str) -> bool:
        return any("негативные эмоции" in item.lower() for item in contract) or bool(
            re.search(r"негатив|эмоц|раздраж|крити|возмущ", prompt)
        )

    def _request_mentions_positive_attitude(self, contract: list[str], prompt: str) -> bool:
        return any("позитивно" in item.lower() for item in contract) or bool(
            re.search(r"позитив|нравит|положит", prompt)
        )

    def _request_mentions_negative_attitude(self, contract: list[str], prompt: str) -> bool:
        return any("негативно" in item.lower() for item in contract) or bool(
            re.search(r"не нрав|отрицат|претенз|жалоб|проблем", prompt)
        )

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
