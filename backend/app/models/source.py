from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin, UpdatedAtMixin
from app.models.enums import PlatformEnum, SourceStatusEnum, SourceTypeEnum


class Source(UUIDMixin, TimestampMixin, UpdatedAtMixin, Base):
    __tablename__ = "sources"
    __table_args__ = (
        Index("ix_sources_project_id", "project_id"),
        UniqueConstraint("project_id", "source_url", name="uq_sources_project_id_source_url"),
    )

    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id"), nullable=False)
    platform: Mapped[PlatformEnum] = mapped_column(Enum(PlatformEnum, name="platform_enum"), nullable=False)
    source_type: Mapped[SourceTypeEnum] = mapped_column(Enum(SourceTypeEnum, name="source_type_enum"), nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    external_source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscriber_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[SourceStatusEnum] = mapped_column(
        Enum(SourceStatusEnum, name="source_status_enum"), default=SourceStatusEnum.pending, nullable=False
    )
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project = relationship("Project", back_populates="sources")
    posts = relationship("Post", back_populates="source", cascade="all, delete-orphan")
