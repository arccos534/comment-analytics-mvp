from __future__ import annotations

from collections import Counter, defaultdict


class ReportAggregator:
    def build_report(self, run, enriched_comments: list[dict], filters: dict) -> dict:
        relevant_comments = [item for item in enriched_comments if item["relevance_score"] >= 0.05]
        working_set = relevant_comments or enriched_comments

        sentiment_counter = Counter(item["sentiment"] for item in working_set)
        topic_counter = Counter(topic for item in working_set for topic in item["topics"])
        post_scores: dict[str, dict] = defaultdict(
            lambda: {
                "post_id": None,
                "post_url": "",
                "post_text": None,
                "positive": 0,
                "negative": 0,
                "comments_count": 0,
            }
        )

        for item in working_set:
            post = item["post"]
            bucket = post_scores[str(post.id)]
            bucket["post_id"] = str(post.id)
            bucket["post_url"] = post.post_url
            bucket["post_text"] = post.post_text
            bucket["comments_count"] += 1
            if item["sentiment"] == "positive":
                bucket["positive"] += 1
            if item["sentiment"] == "negative":
                bucket["negative"] += 1

        total_comments = len(working_set)
        total_posts = len({str(item["post"].id) for item in working_set})
        total_comments_base = max(total_comments, 1)

        topics = [
            {"name": name, "count": count, "share": round(count / total_comments_base, 2)}
            for name, count in topic_counter.most_common(6)
        ]

        liked_patterns = [name for name, count in topic_counter.items() if count >= 2 and "negative" not in name.lower()][:4]
        disliked_patterns = []
        if any(item["sentiment"] == "negative" for item in working_set):
            disliked_patterns = [
                keyword
                for keyword, count in Counter(
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

        top_positive = sorted(
            (
                {
                    "post_id": value["post_id"],
                    "post_url": value["post_url"],
                    "post_text": value["post_text"],
                    "score": round(value["positive"] / max(value["comments_count"], 1), 2),
                    "comments_count": value["comments_count"],
                }
                for value in post_scores.values()
            ),
            key=lambda item: (item["score"], item["comments_count"]),
            reverse=True,
        )[:5]

        top_negative = sorted(
            (
                {
                    "post_id": value["post_id"],
                    "post_url": value["post_url"],
                    "post_text": value["post_text"],
                    "score": round(value["negative"] / max(value["comments_count"], 1), 2),
                    "comments_count": value["comments_count"],
                }
                for value in post_scores.values()
            ),
            key=lambda item: (item["score"], item["comments_count"]),
            reverse=True,
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
                "liked_patterns": liked_patterns or ["Скорость и удобство"],
                "disliked_patterns": disliked_patterns or ["Цена", "Нестабильность качества"],
            },
            "examples": examples,
            "posts": {
                "top_positive": top_positive,
                "top_negative": top_negative,
            },
            "summary": {
                "highlights": [f"Преобладающая тема: {topics[0]['name']}" if topics else "Данных недостаточно"],
                "risks": disliked_patterns[:3] or ["Нужно больше негативных кейсов для анализа"],
                "recommendations": self._build_recommendations(liked_patterns, disliked_patterns),
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

    def _build_recommendations(self, liked_patterns: list[str], disliked_patterns: list[str]) -> list[str]:
        recommendations: list[str] = []
        if liked_patterns:
            recommendations.append(f"Усиливать коммуникацию вокруг темы '{liked_patterns[0]}'.")
        if disliked_patterns:
            recommendations.append(f"Подготовить ответ на претензии по теме '{disliked_patterns[0]}'.")
        if not recommendations:
            recommendations.append("Собрать больше релевантных комментариев по выбранной теме.")
        return recommendations
