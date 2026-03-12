from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.analytics.aggregator import ReportAggregator
from app.analytics.keywords import KeywordExtractor
from app.analytics.relevance import RelevanceScorer
from app.analytics.sentiment import SentimentAnalyzer
from app.analytics.topics import TopicGrouper
from app.core.config import get_settings
from app.models.analysis_run import AnalysisRun
from app.models.enums import AnalysisRunStatusEnum
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.comment_repository import CommentRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.analytics import AnalysisCreateRequest
from app.services.report_service import ReportService
from app.utils.dates import utcnow


class AnalyticsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.comments = CommentRepository(db)
        self.analysis_repo = AnalysisRepository(db)
        self.sentiment = SentimentAnalyzer()
        self.keywords = KeywordExtractor()
        self.topics = TopicGrouper()
        self.relevance = RelevanceScorer()
        self.aggregator = ReportAggregator()
        self.report_service = ReportService()

    def project_exists(self, project_id: UUID) -> bool:
        return self.projects.exists(project_id)

    def create_and_enqueue_run(self, project_id: UUID, payload: AnalysisCreateRequest):
        run = AnalysisRun(
            project_id=project_id,
            prompt_text=payload.prompt_text,
            theme=payload.theme,
            keywords_json=payload.keywords,
            period_from=payload.period_from,
            period_to=payload.period_to,
            filters_json={
                "platforms": [platform.value for platform in payload.platforms],
                "source_ids": [str(source_id) for source_id in payload.source_ids],
            },
            status=AnalysisRunStatusEnum.pending,
        )
        run = self.analysis_repo.create_run(run)
        settings = get_settings()
        if settings.demo_mode or not settings.background_jobs_enabled:
            self.execute_run_sync(run.id)
            refreshed = self.analysis_repo.get_run(run.id)
            return refreshed or run
        try:
            from app.tasks.analytics_tasks import run_analysis_task

            run_analysis_task.delay(str(run.id))
        except Exception:
            self.execute_run_sync(run.id)
        return run

    def get_run(self, analysis_run_id: UUID):
        return self.analysis_repo.get_run(analysis_run_id)

    def get_report(self, analysis_run_id: UUID):
        return self.analysis_repo.get_report(analysis_run_id)

    def execute_run_sync(self, analysis_run_id: UUID) -> dict:
        run = self.analysis_repo.update_run_status(analysis_run_id, AnalysisRunStatusEnum.running)
        if not run:
            return {"status": "not_found"}
        try:
            platform_filters = (run.filters_json or {}).get("platforms") or []
            source_filters = [UUID(value) for value in ((run.filters_json or {}).get("source_ids") or [])]
            records = self.comments.get_analysis_records(
                run.project_id,
                period_from=run.period_from,
                period_to=run.period_to,
                source_ids=source_filters,
                platforms=platform_filters,
            )

            enriched_comments: list[dict] = []
            for comment, post, source in records:
                extracted_keywords = self.keywords.extract(comment.text)
                topics = self.topics.group(extracted_keywords, comment.text)
                relevance_score = self.relevance.score(
                    text=comment.text,
                    prompt_text=run.prompt_text,
                    theme=run.theme,
                    keywords=run.keywords_json or [],
                )
                sentiment_result = self.sentiment.analyze(comment.text)
                self.analysis_repo.upsert_comment_analysis(
                    comment_id=comment.id,
                    sentiment=sentiment_result["sentiment"],
                    sentiment_score=sentiment_result["score"],
                    topics_json=topics,
                    keywords_json=extracted_keywords,
                    relevance_score=relevance_score,
                )
                enriched_comments.append(
                    {
                        "comment": comment,
                        "post": post,
                        "source": source,
                        "sentiment": sentiment_result["sentiment"].value,
                        "sentiment_score": sentiment_result["score"],
                        "topics": topics,
                        "keywords": extracted_keywords,
                        "relevance_score": relevance_score,
                    }
                )

            report_json = self.aggregator.build_report(
                run=run,
                enriched_comments=enriched_comments,
                filters={
                    "platforms": platform_filters,
                    "source_ids": [str(source_id) for source_id in source_filters],
                },
            )
            summary_text = self.report_service.build_summary_text(report_json)
            self.analysis_repo.replace_report_snapshot(run.id, report_json, summary_text)
            self.analysis_repo.update_run_status(run.id, AnalysisRunStatusEnum.completed, finished_at=utcnow())
            return {"status": "completed", "analysis_run_id": str(run.id)}
        except Exception:
            self.analysis_repo.update_run_status(run.id, AnalysisRunStatusEnum.failed, finished_at=utcnow())
            return {"status": "failed", "analysis_run_id": str(run.id)}
