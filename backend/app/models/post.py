from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Post(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "posts"
    __table_args__ = (
        Index("ix_posts_source_id_post_date", "source_id", "post_date"),
        UniqueConstraint("source_id", "external_post_id", name="uq_posts_source_id_external_post_id"),
    )

    source_id: Mapped[UUID] = mapped_column(ForeignKey("sources.id"), nullable=False)
    external_post_id: Mapped[str] = mapped_column(String(255), nullable=False)
    post_url: Mapped[str] = mapped_column(Text, nullable=False)
    post_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    views_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comments_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    source = relationship("Source", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
