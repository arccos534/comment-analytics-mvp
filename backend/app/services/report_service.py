from __future__ import annotations

from app.analytics.llm_report import SummaryGenerator


class ReportService:
    def __init__(self) -> None:
        self.summary_generator = SummaryGenerator()

    def build_summary(self, report_json: dict, prompt_text: str | None = None) -> tuple[dict, str]:
        summary_text = self.summary_generator.generate_summary_text(report_json, prompt_text=prompt_text)
        summary_data = self._build_structured_summary(report_json, prompt_text=prompt_text, summary_text=summary_text)
        return summary_data, summary_text

    def _build_structured_summary(self, report_json: dict, prompt_text: str | None, summary_text: str) -> dict:
        meta = report_json.get("meta", {})
        stats = report_json.get("stats", {})
        sentiment = report_json.get("sentiment", {})
        topics = report_json.get("topics", [])
        insights = report_json.get("insights", {})
        posts = report_json.get("posts", {})

        total_posts = int(stats.get("total_posts", 0) or 0)
        total_comments = int(stats.get("total_comments", 0) or 0)
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)
        coverage_ratio = analyzed_comments / total_comments if total_comments else 0

        return {
            "focus": self._build_focus(meta, prompt_text),
            "answer_to_prompt": self._build_answer_to_prompt(summary_text, analyzed_comments),
            "what_audience_likes": self._build_signal_list(
                liked_patterns=insights.get("liked_patterns", []) or [],
                fallback_prefix="Позитивные сигналы почти не выделяются в явном виде.",
                examples=report_json.get("examples", {}).get("positive_comments", []) or [],
            ),
            "what_audience_dislikes": self._build_signal_list(
                liked_patterns=insights.get("disliked_patterns", []) or [],
                fallback_prefix="Явные повторяющиеся причины негатива выражены слабо.",
                examples=report_json.get("examples", {}).get("negative_comments", []) or [],
            ),
            "interest_drivers": self._build_interest_drivers(topics, posts),
            "limitations": self._build_limitations(total_posts, total_comments, analyzed_comments, coverage_ratio, sentiment),
        }

    def _build_focus(self, meta: dict, prompt_text: str | None) -> str:
        parts: list[str] = []
        post_theme = (meta.get("post_theme") or "").strip()
        post_keywords = meta.get("post_keywords") or []
        if post_theme:
            parts.append(f"Тема постов: {post_theme}.")
        elif post_keywords:
            parts.append(f"Фильтр по постам: {', '.join(post_keywords[:6])}.")
        else:
            parts.append("Тема постов явно не задана.")

        if prompt_text and prompt_text.strip():
            parts.append(f"Фокус анализа комментариев: {prompt_text.strip()}.")

        return " ".join(parts)

    def _build_answer_to_prompt(self, summary_text: str, analyzed_comments: int) -> str:
        if analyzed_comments <= 0:
            return "По выбранной теме и фильтрам не нашлось достаточного количества релевантных комментариев для уверенного ответа на запрос."
        return summary_text

    def _build_signal_list(self, liked_patterns: list[str], fallback_prefix: str, examples: list[dict]) -> list[str]:
        items: list[str] = []
        if liked_patterns:
            items.append(f"Чаще всего встречаются сигналы по темам: {', '.join(liked_patterns[:4])}.")
        for example in examples[:2]:
            text = (example.get("text") or "").strip()
            if text:
                items.append(f"Показательный комментарий: {self._shorten(text)}")
        return items or [fallback_prefix]

    def _build_interest_drivers(self, topics: list[dict], posts: dict) -> list[str]:
        items: list[str] = []
        if topics:
            top_topic_names = ", ".join(topic["name"] for topic in topics[:3])
            items.append(f"Наибольший объем обсуждений собрали темы: {top_topic_names}.")

        popular_posts = posts.get("top_popular", []) or []
        if popular_posts:
            lead_post = popular_posts[0]
            post_text = self._shorten(lead_post.get("post_text") or "")
            if post_text:
                items.append(f"Самый вовлекающий пост в выборке: {post_text}")

        matched_posts = posts.get("matched", []) or []
        if len(matched_posts) >= 3:
            items.append(f"В тематическую выборку попало {len(matched_posts)} релевантных постов.")

        return items or ["Выраженные драйверы интереса по текущей выборке не выделяются."]

    def _build_limitations(
        self,
        total_posts: int,
        total_comments: int,
        analyzed_comments: int,
        coverage_ratio: float,
        sentiment: dict,
    ) -> list[str]:
        limitations: list[str] = []

        if total_posts < 3:
            limitations.append("В выборке слишком мало постов для устойчивых выводов.")
        if analyzed_comments < 20:
            limitations.append("Количество релевантных комментариев низкое, поэтому выводы стоит считать предварительными.")
        if total_comments and coverage_ratio < 0.25:
            limitations.append("В анализ попала только часть собранных комментариев, потому что фильтр темы или prompt сильно сужает выборку.")
        if float(sentiment.get("neutral_percent", 0) or 0) >= 90 and analyzed_comments < 50:
            limitations.append("Преобладание нейтральных комментариев при небольшой выборке снижает точность выводов о позитиве и негативе.")

        return limitations

    def _shorten(self, value: str, limit: int = 140) -> str:
        compact = " ".join(value.split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3].rstrip() + "..."
