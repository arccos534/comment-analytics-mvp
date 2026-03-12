from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import AnalysisRunStatusEnum


class AnalysisRun(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "analysis_runs"
    __table_args__ = (Index("ix_analysis_runs_project_id_created_at", "project_id", "created_at"),)

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    theme: Mapped[str | None] = mapped_column(Text, nullable=True)
    keywords_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    period_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filters_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[AnalysisRunStatusEnum] = mapped_column(
        Enum(AnalysisRunStatusEnum, name="analysis_run_status_enum"),
        default=AnalysisRunStatusEnum.pending,
        nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="analysis_runs")
    report_snapshots = relationship("ReportSnapshot", back_populates="analysis_run", cascade="all, delete-orphan")
