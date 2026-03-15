from __future__ import annotations

from collections import Counter, defaultdict


class ReportAggregator:
    def build_report(self, run, enriched_comments: list[dict], filters: dict, scoped_posts: list[dict] | None = None) -> dict:
        relevant_comments = [item for item in enriched_comments if item["relevance_score"] >= 0.05]
        working_set = relevant_comments or enriched_comments
        scoped_posts = scoped_posts or []

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
                "relevant_comments_count": 0,
                "positive_relevant_comments_count": 0,
                "negative_relevant_comments_count": 0,
                "neutral_relevant_comments_count": 0,
                "platform_comments_count": 0,
                "likes_count": 0,
                "reposts_count": 0,
                "views_count": 0,
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
            bucket["relevant_comments_count"] += 1
            sentiment = item["sentiment"]
            if sentiment in {"positive", "negative", "neutral"}:
                bucket[f"{sentiment}_relevant_comments_count"] += 1
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
            bucket["platform_comments_count"] = max(bucket["platform_comments_count"], getattr(post, "comments_count", 0))
            bucket["likes_count"] = getattr(post, "likes_count", 0)
            bucket["reposts_count"] = getattr(post, "reposts_count", 0)
            bucket["views_count"] = getattr(post, "views_count", 0)

        total_comments = len(working_set)
        total_posts = len(post_scores)
        total_comments_base = max(total_comments, 1)

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

        def popularity_score(value: dict) -> float:
            comments_score = value["platform_comments_count"] * 5
            likes_score = value["likes_count"] * 2
            reposts_score = value["reposts_count"] * 4
            return round(comments_score + likes_score + reposts_score, 2)

        post_items = [
            {
                "post_id": value["post_id"],
                "post_url": value["post_url"],
                "post_text": value["post_text"],
                "platform": value["platform"],
                "source_id": value["source_id"],
                "source_title": value["source_title"],
                "source_url": value["source_url"],
                "score": popularity_score(value),
                "comments_count": value["platform_comments_count"],
                "relevant_comments_count": value["relevant_comments_count"],
                "positive_relevant_comments_count": value["positive_relevant_comments_count"],
                "negative_relevant_comments_count": value["negative_relevant_comments_count"],
                "neutral_relevant_comments_count": value["neutral_relevant_comments_count"],
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
                "posts_count": 0,
                "comments_count": 0,
                "relevant_comments_count": 0,
                "positive_relevant_comments_count": 0,
                "negative_relevant_comments_count": 0,
                "neutral_relevant_comments_count": 0,
                "likes_count": 0,
                "reposts_count": 0,
            }
        )

        for item in post_items:
            source_id = str(item.get("source_id") or "")
            if not source_id:
                continue
            bucket = source_scores[source_id]
            bucket["source_id"] = source_id
            bucket["source_title"] = item.get("source_title")
            bucket["source_url"] = item.get("source_url")
            bucket["platform"] = item.get("platform")
            bucket["posts_count"] += 1
            bucket["comments_count"] += int(item.get("comments_count", 0) or 0)
            bucket["relevant_comments_count"] += int(item.get("relevant_comments_count", 0) or 0)
            bucket["positive_relevant_comments_count"] += int(item.get("positive_relevant_comments_count", 0) or 0)
            bucket["negative_relevant_comments_count"] += int(item.get("negative_relevant_comments_count", 0) or 0)
            bucket["neutral_relevant_comments_count"] += int(item.get("neutral_relevant_comments_count", 0) or 0)
            bucket["likes_count"] += int(item.get("likes_count", 0) or 0)
            bucket["reposts_count"] += int(item.get("reposts_count", 0) or 0)

        source_items = []
        for value in source_scores.values():
            score = popularity_score(value)
            source_items.append(
                {
                    "source_id": value["source_id"],
                    "source_title": value["source_title"],
                    "source_url": value["source_url"],
                    "platform": value["platform"],
                    "posts_count": value["posts_count"],
                    "comments_count": value["comments_count"],
                    "relevant_comments_count": value["relevant_comments_count"],
                    "positive_relevant_comments_count": value["positive_relevant_comments_count"],
                    "negative_relevant_comments_count": value["negative_relevant_comments_count"],
                    "neutral_relevant_comments_count": value["neutral_relevant_comments_count"],
                    "likes_count": value["likes_count"],
                    "reposts_count": value["reposts_count"],
                    "score": score,
                }
            )
        source_items = sorted(
            source_items,
            key=lambda item: (
                item["score"],
                item["comments_count"],
                item["likes_count"],
                item["reposts_count"],
            ),
            reverse=True,
        )

        matched_posts = sorted(
            post_items,
            key=lambda item: (item["relevant_comments_count"], item["comments_count"], item["score"]),
            reverse=True,
        )
        popular_posts = sorted(
            post_items,
            key=lambda item: (item["score"], item["comments_count"], item["likes_count"], item["reposts_count"]),
            reverse=True,
        )[:5]
        unpopular_posts = sorted(
            post_items,
            key=lambda item: (item["score"], item["comments_count"], item["likes_count"], item["reposts_count"]),
        )[:5]

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
                    "relevance_score": item["relevance_score"],
                    "post_url": item["post"].post_url,
                }
            )
            if len(examples) == 3:
                break
        return examples
