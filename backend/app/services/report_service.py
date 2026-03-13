from app.analytics.llm_report import SummaryGenerator


class ReportService:
    def __init__(self) -> None:
        self.summary_generator = SummaryGenerator()

    def build_summary_text(self, report_json: dict, prompt_text: str | None = None) -> str:
        return self.summary_generator.generate_summary_text(report_json, prompt_text=prompt_text)
