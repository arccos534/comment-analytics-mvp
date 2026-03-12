from uuid import UUID

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class ReportSnapshot(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "report_snapshots"

    analysis_run_id: Mapped[UUID] = mapped_column(ForeignKey("analysis_runs.id"), nullable=False)
    report_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    analysis_run = relationship("AnalysisRun", back_populates="report_snapshots")
