from uuid import UUID

from sqlalchemy import Enum, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import SentimentEnum


class CommentAnalysis(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "comment_analysis"
    __table_args__ = (Index("ix_comment_analysis_sentiment", "sentiment"),)

    comment_id: Mapped[UUID] = mapped_column(ForeignKey("comments.id"), unique=True, nullable=False)
    sentiment: Mapped[SentimentEnum] = mapped_column(Enum(SentimentEnum, name="sentiment_enum"), nullable=False)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    topics_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    keywords_json: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    toxicity_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    relevance_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    comment = relationship("Comment", back_populates="analysis")
