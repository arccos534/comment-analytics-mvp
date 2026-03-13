from __future__ import annotations

from openai import OpenAI

from app.core.config import get_settings


class SummaryGenerator:
    def __init__(self) -> None:
        self.settings = get_settings()

    def generate_summary_text(self, report_json: dict, prompt_text: str | None = None) -> str:
        if self.settings.llm_summary_enabled and self.settings.openai_compatible_base_url and self.settings.openai_compatible_api_key:
            try:
                client = OpenAI(
                    base_url=self.settings.openai_compatible_base_url,
                    api_key=self.settings.openai_compatible_api_key,
                )
                completion = client.chat.completions.create(
                    model=self.settings.openai_compatible_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Сформируй короткое резюме отчета по комментариям. "
                                "Theme и keywords относятся к постам и новостям, "
                                "а prompt определяет фокус анализа комментариев. "
                                "Верни 3-5 предложений."
                            ),
                        },
                        {
                            "role": "user",
                            "content": f"Prompt for comment analysis: {prompt_text or 'not provided'}\nReport: {report_json}",
                        },
                    ],
                )
                content = completion.choices[0].message.content
                if content:
                    return content
            except Exception:
                pass

        sentiment = report_json.get("sentiment", {})
        topics = report_json.get("topics", [])
        lead_topic = topics[0]["name"] if topics else "общая реакция"
        return (
            f"Отчет собран по теме постов '{lead_topic}'. "
            f"Позитив: {sentiment.get('positive_percent', 0)}%, "
            f"негатив: {sentiment.get('negative_percent', 0)}%, "
            f"нейтрально: {sentiment.get('neutral_percent', 0)}%. "
            f"Основные выводы и рекомендации доступны в структурированном отчете."
        )
