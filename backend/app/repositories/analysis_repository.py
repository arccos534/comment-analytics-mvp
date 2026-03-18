from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.analysis_run import AnalysisRun
from app.models.comment_analysis import CommentAnalysis
from app.models.enums import AnalysisRunStatusEnum, SentimentEnum
from app.models.project import Project
from app.models.report_snapshot import ReportSnapshot


class AnalysisRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_run(self, run: AnalysisRun) -> AnalysisRun:
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, analysis_run_id: UUID) -> AnalysisRun | None:
        return self.db.get(AnalysisRun, analysis_run_id)

    def delete_run(self, analysis_run_id: UUID) -> bool:
        run = self.get_run(analysis_run_id)
        if not run:
            return False
        self.db.delete(run)
        self.db.commit()
        return True

    def list_active_runs(self, project_id: UUID) -> list[AnalysisRun]:
        rows = self.db.execute(
            select(AnalysisRun)
            .where(
                AnalysisRun.project_id == project_id,
                AnalysisRun.status.in_([AnalysisRunStatusEnum.pending, AnalysisRunStatusEnum.running]),
            )
            .order_by(AnalysisRun.created_at.desc())
        )
        return list(rows.scalars().all())

    def update_run_status(
        self,
        analysis_run_id: UUID,
        status: AnalysisRunStatusEnum,
        finished_at: datetime | None = None,
    ) -> AnalysisRun | None:
        run = self.get_run(analysis_run_id)
        if not run:
            return None
        run.status = status
        run.finished_at = finished_at
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def upsert_comment_analysis(
        self,
        comment_id: UUID,
        sentiment: SentimentEnum,
        sentiment_score: float | None,
        topics_json: list[str],
        keywords_json: list[str],
        relevance_score: float | None,
        toxicity_score: float | None = None,
        commit: bool = True,
    ) -> CommentAnalysis:
        analysis = self.db.scalar(select(CommentAnalysis).where(CommentAnalysis.comment_id == comment_id))
        if not analysis:
            analysis = CommentAnalysis(
                comment_id=comment_id,
                sentiment=sentiment,
                sentiment_score=sentiment_score,
                topics_json=topics_json,
                keywords_json=keywords_json,
                relevance_score=relevance_score,
                toxicity_score=toxicity_score,
            )
            self.db.add(analysis)
        else:
            analysis.sentiment = sentiment
            analysis.sentiment_score = sentiment_score
            analysis.topics_json = topics_json
            analysis.keywords_json = keywords_json
            analysis.relevance_score = relevance_score
            analysis.toxicity_score = toxicity_score
        if commit:
            self.db.commit()
            self.db.refresh(analysis)
        return analysis

    def replace_report_snapshot(self, analysis_run_id: UUID, report_json: dict, summary_text: str | None) -> ReportSnapshot:
        self.db.execute(delete(ReportSnapshot).where(ReportSnapshot.analysis_run_id == analysis_run_id))
        snapshot = ReportSnapshot(analysis_run_id=analysis_run_id, report_json=report_json, summary_text=summary_text)
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        return snapshot

    def get_report(self, analysis_run_id: UUID) -> ReportSnapshot | None:
        return self.db.scalar(
            select(ReportSnapshot).where(ReportSnapshot.analysis_run_id == analysis_run_id).order_by(ReportSnapshot.created_at.desc())
        )

    def list_reports_tree(self) -> list[tuple[Project, AnalysisRun, ReportSnapshot]]:
        rows = self.db.execute(
            select(Project, AnalysisRun, ReportSnapshot)
            .join(AnalysisRun, AnalysisRun.project_id == Project.id)
            .join(ReportSnapshot, ReportSnapshot.analysis_run_id == AnalysisRun.id)
            .where(AnalysisRun.status == AnalysisRunStatusEnum.completed)
            .order_by(Project.created_at.desc(), AnalysisRun.created_at.desc())
        )
        return list(rows.all())
