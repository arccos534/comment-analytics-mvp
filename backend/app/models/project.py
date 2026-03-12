from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, UpdatedAtMixin


class Project(UUIDMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "projects"

    user_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    sources = relationship("Source", back_populates="project", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="project", cascade="all, delete-orphan")
