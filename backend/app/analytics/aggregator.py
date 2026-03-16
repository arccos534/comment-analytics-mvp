from __future__ import annotations

from collections import Counter, defaultdict
from math import ceil

from app.analytics.prompt_intent import extract_requested_count, extract_requested_percentage, infer_prompt_mode


class ReportAggregator:
    POSITIVE_HINT_TOKENS = {
        "хорош",
        "отлич",
        "молод",
        "правиль",
        "верно",
        "соглас",
        "спасибо",
        "нрав",
        "любл",
        "поддерж",
        "класс",
        "супер",
        "рад",
        "здоров",
        "побед",
    }

    NEGATIVE_HINT_TOKENS = {
        "плох",
        "ужас",
        "кошмар",
        "мошенн",
        "фальсифик",
        "поддел",
        "обман",
        "вран",
        "лж",
        "шантаж",
        "позор",
        "стыд",
        "дур",
        "ебан",
        "ненавиж",
        "развод",
        "схам",
        "херн",
    }

    def build_report(
        self,
        run,
        enriched_comments: list[dict],
        filters: dict,
        scoped_posts: list[dict] | None = None,
        selected_sources: list[dict] | None = None,
    ) -> dict:
        relevant_comments = [item for item in enriched_comments if item["relevance_score"] >= 0.05]
        working_set = relevant_comments
        scoped_posts = scoped_posts or []
        prompt_modes = set(infer_prompt_mode(run.prompt_text))
        requested_item_count = extract_requested_count(run.prompt_text)
        requested_success_bucket_percent = (
            extract_requested_percentage(run.prompt_text)
            if {"successful_posts_bucket", "underperforming_posts_bucket"} & prompt_modes
            else None
        )

        sentiment_counter = Counter(item["sentiment"] for item in working_set)
        topic_counter = Counter(topic for item in working_set for topic in item["topics"])
        post_scores: dict[str, dict] = defaultdict(
            lambda: {
                "post_id": None,
                "post_url": "",
                "post_text": None,
                "platform": None,
                "source_id": None,
                "source_title": None,
                "source_url": None,
                "source_subscriber_count": None,
                "relevant_comments_count": 0,
                "positive_relevant_comments_count": 0,
                "negative_relevant_comments_count": 0,
                "neutral_relevant_comments_count": 0,
                "platform_comments_count": 0,
                "likes_count": 0,
                "reposts_count": 0,
                "views_count": 0,
                "positive_comment_candidates": [],
                "negative_comment_candidates": [],
                "neutral_comment_candidates": [],
            }
        )

        for item in working_set:
            post = item["post"]
            source = item["source"]
            bucket = post_scores[str(post.id)]
            bucket["post_id"] = str(post.id)
            bucket["post_url"] = post.post_url
            bucket["post_text"] = post.post_text
            bucket["platform"] = getattr(source.platform, "value", str(source.platform))
            bucket["source_id"] = str(source.id)
            bucket["source_title"] = source.title
            bucket["source_url"] = source.source_url
            bucket["source_subscriber_count"] = getattr(source, "subscriber_count", None)
            bucket["relevant_comments_count"] += 1
            sentiment = item["sentiment"]
            if sentiment in {"positive", "negative", "neutral"}:
                bucket[f"{sentiment}_relevant_comments_count"] += 1
                bucket[f"{sentiment}_comment_candidates"].append(
                    {
                        "comment_id": str(item["comment"].id),
                        "text": item["comment"].text,
                        "sentiment": sentiment,
                        "sentiment_score": item.get("sentiment_score"),
                        "topics": item.get("topics", []),
                        "keywords": item.get("keywords", []),
                        "relevance_score": item["relevance_score"],
                        "post_url": item["post"].post_url,
                    }
                )
            bucket["platform_comments_count"] = max(bucket["platform_comments_count"], getattr(post, "comments_count", 0))
            bucket["likes_count"] = getattr(post, "likes_count", 0)
            bucket["reposts_count"] = getattr(post, "reposts_count", 0)
            bucket["views_count"] = getattr(post, "views_count", 0)

        for item in scoped_posts:
            post = item["post"]
            source = item["source"]
            bucket = post_scores[str(post.id)]
            bucket["post_id"] = str(post.id)
            bucket["post_url"] = post.post_url
            bucket["post_text"] = post.post_text
            bucket["platform"] = getattr(source.platform, "value", str(source.platform))
            bucket["source_id"] = str(source.id)
            bucket["source_title"] = source.title
            bucket["source_url"] = source.source_url
            bucket["source_subscriber_count"] = getattr(source, "subscriber_count", None)
            bucket["platform_comments_count"] = max(bucket["platform_comments_count"], getattr(post, "comments_count", 0))
            bucket["likes_count"] = getattr(post, "likes_count", 0)
            bucket["reposts_count"] = getattr(post, "reposts_count", 0)
            bucket["views_count"] = getattr(post, "views_count", 0)

        total_comments = len(working_set)
        total_posts = len(post_scores)
        total_comments_base = max(total_comments, 1)
        ranking_limit = max(5, requested_item_count or 0)

        topics = [
            {"name": name, "count": count, "share": round(count / total_comments_base, 2)}
            for name, count in topic_counter.most_common(6)
        ]

        liked_patterns = [
            keyword
            for keyword, _ in Counter(
                keyword
                for item in working_set
                if item["sentiment"] == "positive"
                for keyword in item["keywords"]
            ).most_common(4)
        ]
        disliked_patterns = [
            keyword
            for keyword, _ in Counter(
                keyword
                for item in working_set
                if item["sentiment"] == "negative"
                for keyword in item["keywords"]
            ).most_common(4)
        ]

        examples = {
            "positive_comments": self._pick_examples(working_set, "positive"),
            "negative_comments": self._pick_examples(working_set, "negative"),
            "neutral_comments": self._pick_examples(working_set, "neutral"),
        }

        def success_score(value: dict) -> float:
            views = int(value.get("views_count", 0) or 0)
            likes = int(value.get("likes_count", 0) or 0)
            comments = int(value.get("platform_comments_count", value.get("comments_count", 0)) or 0)
            reposts = int(value.get("reposts_count", 0) or 0)
            if views > 0:
                return round(views + likes * 40 + comments * 12 + reposts * 20, 2)
            return round(likes * 50 + comments * 15 + reposts * 20, 2)

        def popularity_key(value: dict) -> tuple[int, int, int, int]:
            return (
                int(value.get("views_count", 0) or 0),
                int(value.get("likes_count", 0) or 0),
                int(value.get("platform_comments_count", value.get("comments_count", 0)) or 0),
                int(value.get("reposts_count", 0) or 0),
            )

        def reaction_key(value: dict) -> tuple[int, int, int, int]:
            return (
                int(value.get("likes_count", 0) or 0),
                int(value.get("views_count", 0) or 0),
                int(value.get("platform_comments_count", value.get("comments_count", 0)) or 0),
                int(value.get("reposts_count", 0) or 0),
            )

        def discussion_key(value: dict) -> tuple[int, int, int, int]:
            return (
                int(value.get("platform_comments_count", value.get("comments_count", 0)) or 0),
                int(value.get("likes_count", 0) or 0),
                int(value.get("views_count", 0) or 0),
                int(value.get("reposts_count", 0) or 0),
            )

        post_items = [
            {
                "post_id": value["post_id"],
                "post_url": value["post_url"],
                "post_text": value["post_text"],
                "platform": value["platform"],
                "source_id": value["source_id"],
                "source_title": value["source_title"],
                "source_url": value["source_url"],
                "source_subscriber_count": value["source_subscriber_count"],
                "score": success_score(value),
                "views_count": value["views_count"],
                "comments_count": value["platform_comments_count"],
                "relevant_comments_count": value["relevant_comments_count"],
                "positive_relevant_comments_count": value["positive_relevant_comments_count"],
                "negative_relevant_comments_count": value["negative_relevant_comments_count"],
                "neutral_relevant_comments_count": value["neutral_relevant_comments_count"],
                "positive_comment_examples": self._pick_candidate_examples(value["positive_comment_candidates"], expected_sentiment="positive"),
                "negative_comment_examples": self._pick_candidate_examples(value["negative_comment_candidates"], expected_sentiment="negative"),
                "neutral_comment_examples": self._pick_candidate_examples(value["neutral_comment_candidates"], expected_sentiment="neutral"),
                "likes_count": value["likes_count"],
                "reposts_count": value["reposts_count"],
            }
            for value in post_scores.values()
        ]

        source_scores: dict[str, dict] = defaultdict(
            lambda: {
                "source_id": None,
                "source_title": None,
                "source_url": None,
                "platform": None,
                "subscriber_count": None,
                "posts_count": 0,
                "views_count": 0,
                "comments_count": 0,
                "relevant_comments_count": 0,
                "positive_relevant_comments_count": 0,
                "negative_relevant_comments_count": 0,
                "neutral_relevant_comments_count": 0,
                "likes_count": 0,
                "reposts_count": 0,
            }
        )

        for source in selected_sources or []:
            source_id = str(source.get("source_id") or "")
            if not source_id:
                continue
            bucket = source_scores[source_id]
            bucket["source_id"] = source_id
            bucket["source_title"] = source.get("source_title")
            bucket["source_url"] = source.get("source_url")
            bucket["platform"] = source.get("platform")
            bucket["subscriber_count"] = source.get("subscriber_count")

        for item in post_items:
            source_id = str(item.get("source_id") or "")
            if not source_id:
                continue
            bucket = source_scores[source_id]
            bucket["source_id"] = source_id
            bucket["source_title"] = item.get("source_title")
            bucket["source_url"] = item.get("source_url")
            bucket["platform"] = item.get("platform")
            bucket["subscriber_count"] = item.get("source_subscriber_count")
            bucket["posts_count"] += 1
            bucket["views_count"] += int(item.get("views_count", 0) or 0)
            bucket["comments_count"] += int(item.get("comments_count", 0) or 0)
            bucket["relevant_comments_count"] += int(item.get("relevant_comments_count", 0) or 0)
            bucket["positive_relevant_comments_count"] += int(item.get("positive_relevant_comments_count", 0) or 0)
            bucket["negative_relevant_comments_count"] += int(item.get("negative_relevant_comments_count", 0) or 0)
            bucket["neutral_relevant_comments_count"] += int(item.get("neutral_relevant_comments_count", 0) or 0)
            bucket["likes_count"] += int(item.get("likes_count", 0) or 0)
            bucket["reposts_count"] += int(item.get("reposts_count", 0) or 0)

        source_items = []
        for value in source_scores.values():
            posts_count = max(int(value["posts_count"] or 0), 1)
            score = success_score(value)
            source_items.append(
                {
                    "source_id": value["source_id"],
                    "source_title": value["source_title"],
                    "source_url": value["source_url"],
                    "platform": value["platform"],
                    "subscriber_count": value["subscriber_count"],
                    "posts_count": value["posts_count"],
                    "views_count": value["views_count"],
                    "comments_count": value["comments_count"],
                    "relevant_comments_count": value["relevant_comments_count"],
                    "positive_relevant_comments_count": value["positive_relevant_comments_count"],
                    "negative_relevant_comments_count": value["negative_relevant_comments_count"],
                    "neutral_relevant_comments_count": value["neutral_relevant_comments_count"],
                    "likes_count": value["likes_count"],
                    "reposts_count": value["reposts_count"],
                    "avg_views_per_post": round(value["views_count"] / posts_count, 2),
                    "avg_comments_per_post": round(value["comments_count"] / posts_count, 2),
                    "avg_likes_per_post": round(value["likes_count"] / posts_count, 2),
                    "avg_reposts_per_post": round(value["reposts_count"] / posts_count, 2),
                    "score": score,
                }
            )
        source_items = sorted(
            source_items,
            key=lambda item: (
                item["avg_views_per_post"],
                item["avg_likes_per_post"],
                item["avg_comments_per_post"],
                item["avg_reposts_per_post"],
                item["subscriber_count"] or 0,
            ),
            reverse=True,
        )

        matched_posts = sorted(
            post_items,
            key=lambda item: (
                item["relevant_comments_count"],
                item["comments_count"],
                item["views_count"],
                item["likes_count"],
            ),
            reverse=True,
        )
        popular_posts = sorted(post_items, key=popularity_key, reverse=True)[:ranking_limit]
        unpopular_posts = sorted(post_items, key=popularity_key)[:ranking_limit]
        reacted_posts = sorted(post_items, key=reaction_key, reverse=True)[:ranking_limit]
        unreacted_posts = sorted(post_items, key=reaction_key)[:ranking_limit]
        discussed_posts = sorted(post_items, key=discussion_key, reverse=True)[:ranking_limit]
        bottom_discussed_posts = sorted(post_items, key=discussion_key)[:ranking_limit]

        success_bucket_share = (requested_success_bucket_percent or 20) / 100
        top_bucket_count = max(1, ceil(len(post_items) * success_bucket_share)) if post_items else 0
        success_leaders = sorted(post_items, key=popularity_key, reverse=True)[:top_bucket_count]
        success_trailers = sorted(post_items, key=popularity_key)[:top_bucket_count]

        report = {
            "meta": {
                "project_id": str(run.project_id),
                "prompt_text": run.prompt_text,
                "post_theme": run.theme,
                "post_keywords": run.keywords_json or [],
                "period_from": run.period_from.isoformat() if run.period_from else None,
                "period_to": run.period_to.isoformat() if run.period_to else None,
                "platforms": filters.get("platforms", []),
                "source_ids": filters.get("source_ids", []),
                "requested_item_count": requested_item_count,
                "requested_success_bucket_percent": requested_success_bucket_percent,
                "analysis_mode_override": (run.filters_json or {}).get("analysis_mode_override"),
            },
            "stats": {
                "total_posts": total_posts,
                "total_comments": len(enriched_comments),
                "analyzed_comments": total_comments,
            },
            "sentiment": {
                "positive_percent": round(100 * sentiment_counter.get("positive", 0) / total_comments_base, 1),
                "negative_percent": round(100 * sentiment_counter.get("negative", 0) / total_comments_base, 1),
                "neutral_percent": round(100 * sentiment_counter.get("neutral", 0) / total_comments_base, 1),
            },
            "topics": topics,
            "insights": {
                "liked_patterns": liked_patterns,
                "disliked_patterns": disliked_patterns,
            },
            "examples": examples,
            "posts": {
                "matched": matched_posts,
                "top_popular": popular_posts,
                "top_unpopular": unpopular_posts,
                "top_reacted": reacted_posts,
                "top_unreacted": unreacted_posts,
                "top_discussed": discussed_posts,
                "top_undiscussed": bottom_discussed_posts,
                "success_top_bucket": success_leaders,
                "success_bottom_bucket": success_trailers,
            },
            "sources": {
                "comparison": source_items,
            },
            "summary": {
                "highlights": [],
                "risks": [],
                "recommendations": [],
            },
        }
        return report

    def _pick_examples(self, items: list[dict], sentiment: str) -> list[dict]:
        subset = [item for item in items if item["sentiment"] == sentiment]
        subset = sorted(subset, key=lambda item: item["relevance_score"], reverse=True)[:3]
        seen: set[str] = set()
        examples: list[dict] = []
        for item in subset:
            fingerprint = item["comment"].text.strip().lower()
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            examples.append(
                {
                    "comment_id": str(item["comment"].id),
                    "text": item["comment"].text,
                    "sentiment": item["sentiment"],
                    "sentiment_score": item.get("sentiment_score"),
                    "topics": item.get("topics", []),
                    "keywords": item.get("keywords", []),
                    "relevance_score": item["relevance_score"],
                    "post_url": item["post"].post_url,
                }
            )
            if len(examples) == 3:
                break
        return examples

    def _pick_candidate_examples(
        self,
        items: list[dict],
        limit: int = 3,
        expected_sentiment: str | None = None,
    ) -> list[dict]:
        subset = sorted(items, key=lambda item: item.get("relevance_score", 0), reverse=True)
        aligned_subset = [
            item for item in subset
            if self._matches_expected_comment_sentiment(item, expected_sentiment)
        ]
        if expected_sentiment:
            subset = aligned_subset
        seen: set[str] = set()
        examples: list[dict] = []
        for item in subset:
            fingerprint = (item.get("text") or "").strip().lower()
            if not fingerprint or fingerprint in seen:
                continue
            seen.add(fingerprint)
            examples.append(
                {
                    "comment_id": item.get("comment_id"),
                    "text": item.get("text") or "",
                    "sentiment": item.get("sentiment"),
                    "sentiment_score": item.get("sentiment_score"),
                    "topics": item.get("topics", []),
                    "keywords": item.get("keywords", []),
                    "relevance_score": item.get("relevance_score"),
                    "post_url": item.get("post_url"),
                }
            )
            if len(examples) >= limit:
                break
        return examples

    def _matches_expected_comment_sentiment(self, item: dict, expected_sentiment: str | None) -> bool:
        if not expected_sentiment or expected_sentiment == "neutral":
            return True

        text = item.get("text") or ""
        base_sentiment = item.get("sentiment")
        try:
            base_score = float(item.get("sentiment_score") or 0.0)
        except (TypeError, ValueError):
            base_score = 0.0
        positive_hits, negative_hits = self._comment_sentiment_hints(text)
        if expected_sentiment == "positive":
            if base_sentiment == "negative" or base_score <= 0:
                return False
            if negative_hits > positive_hits:
                return False
            if positive_hits == 0 and base_score < 0.18:
                return False
            return True
        if expected_sentiment == "negative":
            if base_sentiment == "positive" or base_score >= 0:
                return False
            if positive_hits > negative_hits:
                return False
            if negative_hits == 0 and base_score > -0.18:
                return False
            return True
        return True

    def _comment_sentiment_hints(self, text: str) -> tuple[int, int]:
        normalized = (text or "").strip().lower().replace("ё", "е")
        positive_hits = sum(1 for token in self.POSITIVE_HINT_TOKENS if token in normalized)
        negative_hits = sum(1 for token in self.NEGATIVE_HINT_TOKENS if token in normalized)
        return positive_hits, negative_hits
