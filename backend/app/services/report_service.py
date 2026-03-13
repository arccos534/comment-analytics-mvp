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

        total_posts = int(stats.get("total_posts", 0) or 0)
        total_comments = int(stats.get("total_comments", 0) or 0)
        analyzed_comments = int(stats.get("analyzed_comments", 0) or 0)
        coverage_ratio = analyzed_comments / total_comments if total_comments else 0

        focus_lines = []
        if meta.get("post_theme"):
            focus_lines.append(f"Тема постов: {meta['post_theme']}.")
        elif meta.get("post_keywords"):
            focus_lines.append(f"Фильтр по постам: {', '.join(meta['post_keywords'])}.")
        else:
            focus_lines.append("Тема постов явно не задана.")

        if prompt_text:
            focus_lines.append(f"Фокус анализа комментариев: {prompt_text.strip()}.")

        verdict = self._build_verdict(sentiment, topics, analyzed_comments)
        key_points = self._build_key_points(topics, insights, total_posts, analyzed_comments)
        limitations = self._build_limitations(total_posts, total_comments, analyzed_comments, coverage_ratio)

        return {
            "focus": " ".join(focus_lines),
            "verdict": verdict,
            "key_points": key_points,
            "limitations": limitations,
            "overview": summary_text,
        }

    def _build_verdict(self, sentiment: dict, topics: list[dict], analyzed_comments: int) -> str:
        if analyzed_comments <= 0:
            return "Данных для анализа комментариев пока недостаточно."

        lead_topic = topics[0]["name"] if topics else "общих обсуждений"
        positive = float(sentiment.get("positive_percent", 0) or 0)
        negative = float(sentiment.get("negative_percent", 0) or 0)
        neutral = float(sentiment.get("neutral_percent", 0) or 0)

        if negative >= max(positive + 5, 15):
            tone = "преимущественно негативная"
        elif positive >= max(negative + 5, 15):
            tone = "преимущественно позитивная"
        elif neutral >= 70:
            tone = "в основном нейтральная"
        else:
            tone = "смешанная"

        return f"По доступным комментариям реакция аудитории {tone}; основной массив обсуждений связан с темой «{lead_topic}»."

    def _build_key_points(self, topics: list[dict], insights: dict, total_posts: int, analyzed_comments: int) -> list[str]:
        points: list[str] = []

        if total_posts:
            points.append(f"В выборку попало {total_posts} постов, по которым проанализировано {analyzed_comments} комментариев.")

        if topics:
            visible_topics = ", ".join(topic["name"] for topic in topics[:3])
            points.append(f"Ключевые темы обсуждения: {visible_topics}.")

        liked = insights.get("liked_patterns", []) or []
        disliked = insights.get("disliked_patterns", []) or []
        if liked:
            points.append(f"Позитивные сигналы чаще связаны с: {', '.join(liked[:3])}.")
        if disliked:
            points.append(f"Негативные сигналы чаще связаны с: {', '.join(disliked[:3])}.")

        return points[:4]

    def _build_limitations(
        self,
        total_posts: int,
        total_comments: int,
        analyzed_comments: int,
        coverage_ratio: float,
    ) -> list[str]:
        limitations: list[str] = []

        if total_posts < 3:
            limitations.append("В выборке слишком мало постов для устойчивых выводов.")
        if analyzed_comments < 20:
            limitations.append("Количество релевантных комментариев низкое, поэтому выводы стоит считать предварительными.")
        if total_comments and coverage_ratio < 0.25:
            limitations.append("В анализ попала только часть собранных комментариев, потому что фильтр темы/промта сильно сужает выборку.")

        return limitations
