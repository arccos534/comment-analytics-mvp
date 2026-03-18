from __future__ import annotations

from app.analytics.prompt_intent import extract_requested_count
from app.analytics.llm_report import SummaryGenerator


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
        requested_count = extract_requested_count(prompt_text) or int(meta.get("requested_item_count") or 0) or 5

        overview = "По текущей выборке недостаточно данных для содержательного вывода."
        takeaways: list[str] = []

        if mode == "source_comparison" and sources:
            top_sources = sources[: min(requested_count, 5)]
            lead = top_sources[0]
            overview = (
                f"Лидирующий источник — «{lead.get('source_title') or lead.get('source_url') or 'без названия'}»: "
                f"в среднем {int(lead.get('avg_views_per_post') or 0)} просмотров, "
                f"{int(lead.get('avg_likes_per_post') or 0)} лайков или реакций, "
                f"{int(lead.get('avg_comments_per_post') or 0)} комментариев и "
                f"{int(lead.get('avg_reposts_per_post') or 0)} репостов на пост."
            )
            takeaways.append(overview)
            if len(top_sources) > 1:
                second = top_sources[1]
                takeaways.append(
                    f"Второй источник — «{second.get('source_title') or second.get('source_url') or 'без названия'}»: "
                    f"{int(second.get('avg_views_per_post') or 0)} просмотров и {int(second.get('avg_likes_per_post') or 0)} лайков или реакций в среднем."
                )
            if len(top_sources) > 2:
                titles = [item.get("source_title") or item.get("source_url") or "без названия" for item in top_sources]
                takeaways.append(f"Для сравнения стоит смотреть источники: {', '.join(titles)}.")
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
