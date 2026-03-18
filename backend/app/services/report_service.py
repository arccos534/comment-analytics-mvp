from __future__ import annotations

from app.analytics.llm_report import SummaryGenerator
from app.analytics.prompt_intent import extract_requested_count, infer_source_metric


class ReportService:
    def __init__(self) -> None:
        self.summary_generator = SummaryGenerator()

    def build_summary(
        self,
        report_json: dict,
        prompt_text: str | None = None,
        prompt_route: dict | None = None,
    ) -> tuple[dict, str]:
        if self._should_use_deterministic_summary(prompt_route):
            return self._build_deterministic_summary(report_json, prompt_text, prompt_route or {})
        return self.summary_generator.generate_summary_bundle(report_json, prompt_text=prompt_text)

    def _should_use_deterministic_summary(self, prompt_route: dict | None) -> bool:
        if not prompt_route:
            return False
        if prompt_route.get("needs_llm_reasoning"):
            return False
        return (prompt_route.get("analysis_mode") or "") in {
            "source_comparison",
            "post_popularity",
            "post_underperformance",
        }

    def _build_deterministic_summary(
        self,
        report_json: dict,
        prompt_text: str | None,
        prompt_route: dict,
    ) -> tuple[dict, str]:
        mode = str(prompt_route.get("analysis_mode") or "topic_report")
        meta = report_json.get("meta", {}) or {}
        posts = report_json.get("posts", {}) or {}
        sources = (report_json.get("sources", {}) or {}).get("comparison", []) or []
        default_count = 3 if mode == "source_comparison" else 5
        requested_count = extract_requested_count(prompt_text) or int(meta.get("requested_item_count") or 0) or default_count

        overview = "По текущей выборке недостаточно данных для содержательного вывода."
        takeaways: list[str] = []

        if mode == "source_comparison" and sources:
            source_metric = str(meta.get("requested_source_metric") or infer_source_metric(prompt_text) or "engagement")
            ranked_sources = sorted(sources, key=lambda item: self._source_metric_sort_key(item, source_metric), reverse=True)
            top_sources = ranked_sources[: max(1, min(requested_count, len(ranked_sources), 10))]
            metric_label = self._source_metric_title(source_metric)
            summary_lines = [
                f"{index + 1}. «{item.get('source_title') or item.get('source_url') or 'Источник без названия'}» — {self._format_source_focus_metric(item, source_metric)}"
                for index, item in enumerate(top_sources)
            ]
            overview = f"Топ {len(top_sources)} источников по {metric_label}: {'; '.join(summary_lines)}."
            takeaways.append(overview)
            takeaways.append(
                "Средние метрики по этим источникам: "
                + "; ".join(
                    f"«{item.get('source_title') or item.get('source_url') or 'Источник без названия'}» — {self._format_source_metrics(item)}"
                    for item in top_sources
                )
                + "."
            )
        elif mode == "post_popularity":
            ranked = self._select_ranked_posts(report_json, prompt_text, strongest=True)
            if ranked:
                lead = ranked[0]
                overview = (
                    f"Лидирующий пост — «{lead.get('post_text') or 'без названия'}»: "
                    f"{self._format_post_metrics(lead)}."
                )
                takeaways.append(overview)
                if len(ranked) > 1:
                    takeaways.append(
                        f"Следом идут: {self._join_post_titles(ranked[1 : min(len(ranked), min(requested_count, 3))])}."
                    )
        elif mode == "post_underperformance":
            ranked = self._select_ranked_posts(report_json, prompt_text, strongest=False)
            if ranked:
                lead = ranked[0]
                overview = (
                    f"Наименее сильный пост — «{lead.get('post_text') or 'без названия'}»: "
                    f"{self._format_post_metrics(lead)}."
                )
                takeaways.append(overview)
                if len(ranked) > 1:
                    takeaways.append(
                        f"В числе самых слабых также: {self._join_post_titles(ranked[1 : min(len(ranked), min(requested_count, 3))])}."
                    )

        summary = {
            "overview": overview,
            "takeaways": takeaways[:3],
            "analysis_mode": mode,
            "primary_mode": prompt_route.get("primary_mode") or mode,
            "prompt_modes": prompt_route.get("prompt_modes") or [],
            "secondary_modes": prompt_route.get("secondary_modes") or [],
            "analysis_axes": prompt_route.get("analysis_axes") or [],
            "request_contract": prompt_route.get("request_contract") or [],
            "answer_strategy": prompt_route.get("answer_strategy") or {},
            "confidence_assessment": {
                "level": "high" if report_json.get("stats", {}).get("total_posts", 0) else "low",
                "reason": f"router={prompt_route.get('router_source') or 'deterministic'} confidence={prompt_route.get('confidence') or 0}",
            },
            "theme_reaction_map": [],
            "focus_evidence": [],
            "top_positive_posts": [],
            "top_negative_posts": [],
        }
        return summary, overview

    def _select_ranked_posts(self, report_json: dict, prompt_text: str | None, strongest: bool) -> list[dict]:
        posts = report_json.get("posts", {}) or {}
        lowered = (prompt_text or "").lower()
        if "просмотр" in lowered or "охват" in lowered:
            candidates = list(posts.get("top_popular" if strongest else "top_unpopular", []) or [])
            return sorted(candidates, key=lambda item: int(item.get("views_count") or 0), reverse=strongest)
        if "лайк" in lowered or "реакц" in lowered:
            candidates = list(posts.get("top_reacted" if strongest else "top_unreacted", []) or [])
            return sorted(candidates, key=lambda item: int(item.get("likes_count") or 0), reverse=strongest)
        if "коммент" in lowered:
            candidates = list(posts.get("top_discussed" if strongest else "top_undiscussed", []) or [])
            return sorted(candidates, key=lambda item: int(item.get("comments_count") or 0), reverse=strongest)
        return list(posts.get("top_popular" if strongest else "top_unpopular", []) or [])

    def _format_post_metrics(self, post: dict) -> str:
        views = int(post.get("views_count") or 0)
        likes = int(post.get("likes_count") or 0)
        comments = int(post.get("comments_count") or 0)
        reposts = int(post.get("reposts_count") or 0)
        parts: list[str] = []
        if views > 0:
            parts.append(f"{views} просмотров")
        parts.append(f"{likes} лайков или реакций")
        parts.append(f"{comments} комментариев")
        parts.append(f"{reposts} репостов")
        return ", ".join(parts)

    def _join_post_titles(self, posts: list[dict]) -> str:
        titles = [f"«{(item.get('post_text') or 'без названия')}»" for item in posts if item]
        return ", ".join(titles)

    def _source_metric_sort_key(self, source: dict, metric: str) -> tuple[float, float, float, float, int]:
        if metric == "subscribers":
            return (
                int(source.get("subscriber_count", 0) or 0),
                float(source.get("avg_views_per_post", 0) or 0),
                float(source.get("avg_likes_per_post", 0) or 0),
                float(source.get("avg_comments_per_post", 0) or 0),
                float(source.get("avg_reposts_per_post", 0) or 0),
            )
        if metric == "views":
            return (
                float(source.get("avg_views_per_post", 0) or 0),
                int(source.get("subscriber_count", 0) or 0),
                float(source.get("avg_likes_per_post", 0) or 0),
                float(source.get("avg_comments_per_post", 0) or 0),
                float(source.get("avg_reposts_per_post", 0) or 0),
            )
        if metric == "likes":
            return (
                float(source.get("avg_likes_per_post", 0) or 0),
                float(source.get("avg_views_per_post", 0) or 0),
                float(source.get("avg_comments_per_post", 0) or 0),
                float(source.get("avg_reposts_per_post", 0) or 0),
                int(source.get("subscriber_count", 0) or 0),
            )
        if metric == "comments":
            return (
                float(source.get("avg_comments_per_post", 0) or 0),
                float(source.get("avg_views_per_post", 0) or 0),
                float(source.get("avg_likes_per_post", 0) or 0),
                float(source.get("avg_reposts_per_post", 0) or 0),
                int(source.get("subscriber_count", 0) or 0),
            )
        if metric == "reposts":
            return (
                float(source.get("avg_reposts_per_post", 0) or 0),
                float(source.get("avg_views_per_post", 0) or 0),
                float(source.get("avg_likes_per_post", 0) or 0),
                float(source.get("avg_comments_per_post", 0) or 0),
                int(source.get("subscriber_count", 0) or 0),
            )
        return (
            float(source.get("avg_views_per_post", 0) or 0),
            float(source.get("avg_likes_per_post", 0) or 0),
            float(source.get("avg_comments_per_post", 0) or 0),
            float(source.get("avg_reposts_per_post", 0) or 0),
            int(source.get("subscriber_count", 0) or 0),
        )

    def _format_source_focus_metric(self, source: dict, metric: str) -> str:
        if metric == "subscribers":
            return f"{int(source.get('subscriber_count', 0) or 0)} подписчиков"
        if metric == "views":
            return f"{round(float(source.get('avg_views_per_post', 0) or 0))} просмотров в среднем на пост"
        if metric == "likes":
            return f"{round(float(source.get('avg_likes_per_post', 0) or 0))} лайков или реакций в среднем на пост"
        if metric == "comments":
            return f"{round(float(source.get('avg_comments_per_post', 0) or 0))} комментариев в среднем на пост"
        if metric == "reposts":
            return f"{round(float(source.get('avg_reposts_per_post', 0) or 0))} репостов в среднем на пост"
        return self._format_source_metrics(source)

    def _source_metric_title(self, metric: str) -> str:
        titles = {
            "subscribers": "подписчикам",
            "views": "просмотрам",
            "likes": "лайкам или реакциям",
            "comments": "комментариям",
            "reposts": "репостам",
            "engagement": "совокупности метрик",
        }
        return titles.get(metric, "совокупности метрик")

    def _format_source_metrics(self, source: dict) -> str:
        metric_label = "реакций" if (source.get("platform") or "").lower() == "telegram" else "лайков"
        parts: list[str] = []
        avg_views = round(float(source.get("avg_views_per_post", 0) or 0))
        avg_likes = round(float(source.get("avg_likes_per_post", 0) or 0))
        avg_comments = round(float(source.get("avg_comments_per_post", 0) or 0))
        avg_reposts = round(float(source.get("avg_reposts_per_post", 0) or 0))
        if avg_views > 0:
            parts.append(f"{avg_views} просмотров на пост")
        parts.append(f"{avg_likes} {metric_label} на пост")
        parts.append(f"{avg_comments} комментариев на пост")
        parts.append(f"{avg_reposts} репостов на пост")
        if int(source.get("subscriber_count", 0) or 0) > 0:
            parts.append(f"{int(source.get('subscriber_count', 0) or 0)} подписчиков")
        return ", ".join(parts)
