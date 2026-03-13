from datetime import datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.post import Post
from app.models.source import Source
from app.providers.base import NormalizedComment
from app.utils.normalization import hash_external_author_id


class CommentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_project(self, project_id: UUID) -> list[Comment]:
        stmt = (
            select(Comment)
            .join(Post, Comment.post_id == Post.id)
            .join(Source, Post.source_id == Source.id)
            .where(Source.project_id == project_id)
            .order_by(Comment.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def get_by_post_and_external_id(self, post_id: UUID, external_comment_id: str) -> Comment | None:
        return self.db.scalar(
            select(Comment).where(Comment.post_id == post_id, Comment.external_comment_id == external_comment_id)
        )

    def get_by_post_and_external_ids(self, post_id: UUID, external_comment_ids: list[str]) -> dict[str, Comment]:
        if not external_comment_ids:
            return {}
        stmt = select(Comment).where(Comment.post_id == post_id, Comment.external_comment_id.in_(external_comment_ids))
        return {comment.external_comment_id: comment for comment in self.db.scalars(stmt)}

    def upsert_comments(self, post_id: UUID, normalized_comments: list[NormalizedComment]) -> list[Comment]:
        persisted: list[Comment] = []
        comment_map = self.get_by_post_and_external_ids(
            post_id,
            [comment.external_comment_id for comment in normalized_comments],
        )
        for normalized in normalized_comments:
            comment = comment_map.get(normalized.external_comment_id)
            if not comment:
                comment = Comment(
                    post_id=post_id,
                    external_comment_id=normalized.external_comment_id,
                    text=normalized.text,
                    created_at=normalized.created_at,
                    author_external_id_hash=hash_external_author_id(normalized.author_external_id),
                    author_name=normalized.author_name,
                    language=normalized.language,
                    likes_count=normalized.likes_count,
                    reply_count=normalized.reply_count,
                    raw_payload=normalized.raw_payload,
                )
                self.db.add(comment)
            else:
                comment.text = normalized.text
                comment.created_at = normalized.created_at
                comment.author_external_id_hash = hash_external_author_id(normalized.author_external_id)
                comment.author_name = normalized.author_name
                comment.language = normalized.language
                comment.likes_count = normalized.likes_count
                comment.reply_count = normalized.reply_count
                comment.raw_payload = normalized.raw_payload
            persisted.append(comment)
        self.db.flush()
        return persisted

    def build_analysis_query(
        self,
        project_id: UUID,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
        source_ids: list[UUID] | None = None,
        platforms: list[str] | None = None,
    ) -> Select[tuple[Comment, Post, Source]]:
        stmt = (
            select(Comment, Post, Source)
            .join(Post, Comment.post_id == Post.id)
            .join(Source, Post.source_id == Source.id)
            .where(Source.project_id == project_id)
        )
        if period_from:
            stmt = stmt.where(Comment.created_at >= period_from)
        if period_to:
            stmt = stmt.where(Comment.created_at <= period_to)
        if source_ids:
            stmt = stmt.where(Source.id.in_(source_ids))
        if platforms:
            stmt = stmt.where(Source.platform.in_(platforms))
        return stmt.order_by(Comment.created_at.desc())

    def get_analysis_records(
        self,
        project_id: UUID,
        period_from: datetime | None = None,
        period_to: datetime | None = None,
        source_ids: list[UUID] | None = None,
        platforms: list[str] | None = None,
    ) -> list[tuple[Comment, Post, Source]]:
        return list(self.db.execute(self.build_analysis_query(project_id, period_from, period_to, source_ids, platforms)))
