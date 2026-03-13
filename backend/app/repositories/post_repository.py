from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.post import Post
from app.models.source import Source
from app.providers.base import NormalizedPost


class PostRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_project(self, project_id: UUID) -> list[Post]:
        stmt = (
            select(Post)
            .join(Source, Post.source_id == Source.id)
            .where(Source.project_id == project_id)
            .order_by(Post.post_date.desc())
        )
        return list(self.db.scalars(stmt))

    def get_by_source_and_external_id(self, source_id: UUID, external_post_id: str) -> Post | None:
        return self.db.scalar(
            select(Post).where(Post.source_id == source_id, Post.external_post_id == external_post_id)
        )

    def get_by_source_and_external_ids(self, source_id: UUID, external_post_ids: list[str]) -> dict[str, Post]:
        if not external_post_ids:
            return {}
        stmt = select(Post).where(Post.source_id == source_id, Post.external_post_id.in_(external_post_ids))
        return {post.external_post_id: post for post in self.db.scalars(stmt)}

    def upsert_posts(self, source_id: UUID, normalized_posts: list[NormalizedPost]) -> list[Post]:
        persisted: list[Post] = []
        existing = self.get_by_source_and_external_ids(
            source_id,
            [normalized.external_post_id for normalized in normalized_posts],
        )
        for normalized in normalized_posts:
            post = existing.get(normalized.external_post_id)
            if not post:
                post = Post(
                    source_id=source_id,
                    external_post_id=normalized.external_post_id,
                    post_url=normalized.post_url,
                    post_text=normalized.post_text,
                    post_date=normalized.post_date,
                    likes_count=normalized.likes_count,
                    views_count=normalized.views_count,
                    comments_count=normalized.comments_count,
                    raw_payload=normalized.raw_payload,
                )
                self.db.add(post)
            else:
                post.post_url = normalized.post_url
                post.post_text = normalized.post_text
                post.post_date = normalized.post_date
                post.likes_count = normalized.likes_count
                post.views_count = normalized.views_count
                post.comments_count = normalized.comments_count
                post.raw_payload = normalized.raw_payload
            persisted.append(post)
        self.db.flush()
        return persisted

    def latest_post_date_for_source(self, source_id: UUID) -> datetime | None:
        stmt = select(Post).where(Post.source_id == source_id).order_by(Post.post_date.desc())
        post = self.db.scalar(stmt)
        return post.post_date if post else None
