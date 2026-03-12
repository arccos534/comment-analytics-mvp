from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Comment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_post_id_created_at", "post_id", "created_at"),
        UniqueConstraint("post_id", "external_comment_id", name="uq_comments_post_id_external_comment_id"),
    )

    post_id: Mapped[UUID] = mapped_column(ForeignKey("posts.id"), nullable=False)
    external_comment_id: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_comment_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("comments.id"), nullable=True)
    author_external_id_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    likes_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reply_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    post = relationship("Post", back_populates="comments")
    analysis = relationship("CommentAnalysis", back_populates="comment", uselist=False, cascade="all, delete-orphan")
