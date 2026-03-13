from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import SourceStatusEnum
from app.providers.factory import get_provider
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.source_repository import SourceRepository
from app.utils.dates import utcnow


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.sources = SourceRepository(db)
        self.posts = PostRepository(db)
        self.comments = CommentRepository(db)

    def project_exists(self, project_id: UUID) -> bool:
        return self.projects.exists(project_id)

    def enqueue_project_index(self, project_id: UUID) -> str:
        settings = get_settings()
        if settings.demo_mode or not settings.background_jobs_enabled:
            self.index_project_sources_sync(project_id)
            return "sync-inline"
        try:
            from app.tasks.ingestion_tasks import index_project_sources_task

            task = index_project_sources_task.delay(str(project_id))
            return task.id
        except Exception:
            self.index_project_sources_sync(project_id)
            return "sync-fallback"

    def get_project_index_status(self, project_id: UUID) -> dict:
        sources = self.sources.list_by_project(project_id)
        counts: dict[str, int] = {}
        for source in sources:
            counts[source.status.value] = counts.get(source.status.value, 0) + 1
        return {
            "project_id": str(project_id),
            "total_sources": len(sources),
            "status_breakdown": counts,
            "sources": [
                {
                    "id": str(source.id),
                    "title": source.title,
                    "platform": source.platform.value,
                    "status": source.status.value,
                    "last_indexed_at": source.last_indexed_at.isoformat() if source.last_indexed_at else None,
                }
                for source in sources
            ],
        }

    def index_project_sources_sync(self, project_id: UUID, since: datetime | None = None) -> dict:
        stats = {"sources": 0, "posts": 0, "comments": 0}
        for source in self.sources.list_by_project(project_id):
            result = self.index_single_source_sync(source.id, since=since)
            stats["sources"] += 1
            stats["posts"] += result["posts"]
            stats["comments"] += result["comments"]
        return stats

    def index_single_source_sync(self, source_id: UUID, since: datetime | None = None) -> dict:
        source = self.sources.get(source_id)
        if not source:
            return {"posts": 0, "comments": 0}

        source.status = SourceStatusEnum.indexing
        self.sources.update(source)
        try:
            provider = get_provider(source.platform)
            # A manual project reindex should rebuild the full source history unless
            # the caller explicitly requests an incremental sync via `since`.
            effective_since = since
            posts = provider.fetch_posts(source, since=effective_since)
            persisted_posts = self.posts.upsert_posts(source.id, posts)

            total_comments = 0
            for normalized_post, persisted_post in zip(posts, persisted_posts, strict=False):
                comments = provider.fetch_comments(source, normalized_post)
                self.comments.upsert_comments(persisted_post.id, comments)
                total_comments += len(comments)

            source.status = SourceStatusEnum.ready
            source.last_indexed_at = utcnow()
            self.sources.update(source)
            return {"posts": len(persisted_posts), "comments": total_comments}
        except Exception:
            source.status = SourceStatusEnum.failed
            self.sources.update(source)
            return {"posts": 0, "comments": 0}
