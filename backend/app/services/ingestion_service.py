import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import SourceStatusEnum
from app.providers.factory import get_provider
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.source_repository import SourceRepository
from app.schemas.source import IndexModeEnum, IndexPeriodPresetEnum, IndexRequest
from app.utils.dates import utcnow
from app.utils.index_progress import (
    build_progress_summary,
    clear_current_source,
    finish_source_progress,
    init_project_progress,
    set_source_processed_posts,
    set_source_total_posts,
    start_source_progress,
)
from app.utils.provider_cache import (
    comments_cache_key,
    load_comments,
    load_posts,
    posts_cache_key,
    save_comments,
    save_posts,
)

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.sources = SourceRepository(db)
        self.posts = PostRepository(db)
        self.comments = CommentRepository(db)

    def project_exists(self, project_id: UUID) -> bool:
        return self.projects.exists(project_id)

    def enqueue_project_index(self, project_id: UUID, request: IndexRequest | None = None) -> str:
        settings = get_settings()
        since, until, posts_limit = self._resolve_index_window(request or IndexRequest())
        if settings.demo_mode or not settings.background_jobs_enabled:
            self.index_project_sources_sync(project_id, since=since, until=until, posts_limit=posts_limit)
            return "sync-inline"
        try:
            from app.tasks.ingestion_tasks import index_single_source_task

            queued_ids: list[str] = []
            for source in self.sources.list_by_project(project_id):
                task = index_single_source_task.delay(
                    str(source.id),
                    since.isoformat() if since else None,
                    until.isoformat() if until else None,
                    posts_limit,
                )
                queued_ids.append(task.id)
            return queued_ids[0] if queued_ids else "empty-project"
        except Exception:
            self.index_project_sources_sync(project_id, since=since, until=until, posts_limit=posts_limit)
            return "sync-fallback"

    def get_project_index_status(self, project_id: UUID) -> dict:
        sources = self.sources.list_by_project(project_id)
        counts: dict[str, int] = {}
        for source in sources:
            counts[source.status.value] = counts.get(source.status.value, 0) + 1
        has_active_indexing = (counts.get(SourceStatusEnum.pending.value, 0) + counts.get(SourceStatusEnum.indexing.value, 0)) > 0
        progress = build_progress_summary(str(project_id)) if has_active_indexing else None
        if progress is None and has_active_indexing and sources:
            ready_like = counts.get(SourceStatusEnum.ready.value, 0) + counts.get(SourceStatusEnum.failed.value, 0)
            progress = {
                "percent": round((ready_like / len(sources)) * 100, 1),
                "current_source_title": None,
                "current_source_index": 0,
                "total_sources": len(sources),
                "completed_sources": ready_like,
                "processed_posts": 0,
                "total_posts": 0,
                "posts_label": None,
                "updated_at": None,
                "finished_at": None,
            }
        return {
            "project_id": str(project_id),
            "total_sources": len(sources),
            "status_breakdown": counts,
            "progress": progress,
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

    def index_project_sources_sync(
        self,
        project_id: UUID,
        since: datetime | None = None,
        until: datetime | None = None,
        posts_limit: int | None = None,
    ) -> dict:
        stats = {"sources": 0, "posts": 0, "comments": 0}
        project_sources = self.sources.list_by_project(project_id)
        init_project_progress(str(project_id), len(project_sources))
        for index, source in enumerate(project_sources, start=1):
            start_source_progress(str(project_id), str(source.id), source.title or source.source_url, index)
            result = self.index_single_source_sync(source.id, since=since, until=until, posts_limit=posts_limit)
            stats["sources"] += 1
            stats["posts"] += result["posts"]
            stats["comments"] += result["comments"]
            finish_source_progress(str(project_id))
            clear_current_source(str(project_id))
        return stats

    def index_single_source_sync(
        self,
        source_id: UUID,
        since: datetime | None = None,
        until: datetime | None = None,
        posts_limit: int | None = None,
    ) -> dict:
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
            posts = self._fetch_posts_with_cache(
                provider=provider,
                source=source,
                since=effective_since,
                until=until,
                posts_limit=posts_limit,
            )
            persisted_posts = self.posts.upsert_posts(source.id, posts)
            set_source_total_posts(str(source.project_id), len(posts))

            total_comments = 0
            for index, (normalized_post, persisted_post) in enumerate(zip(posts, persisted_posts, strict=False), start=1):
                try:
                    if normalized_post.comments_count <= 0:
                        continue
                    comments = self._fetch_comments_with_cache(
                        provider=provider,
                        source=source,
                        post=normalized_post,
                    )
                    self.comments.upsert_comments(persisted_post.id, comments)
                    total_comments += len(comments)
                except Exception as exc:
                    logger.warning(
                        "Comment sync skipped for source=%s post=%s platform=%s: %s",
                        source.id,
                        normalized_post.external_post_id,
                        source.platform.value,
                        exc,
                    )
                finally:
                    set_source_processed_posts(str(source.project_id), index)

            self.db.commit()
            source.status = SourceStatusEnum.ready
            source.last_indexed_at = utcnow()
            self.sources.update(source)
            return {"posts": len(persisted_posts), "comments": total_comments}
        except Exception:
            logger.exception(
                "Source indexing failed for source=%s platform=%s since=%s until=%s limit=%s",
                source.id,
                source.platform.value,
                since.isoformat() if since else None,
                until.isoformat() if until else None,
                posts_limit,
            )
            source.status = SourceStatusEnum.failed
            self.sources.update(source)
            return {"posts": 0, "comments": 0}

    def _resolve_index_window(self, request: IndexRequest) -> tuple[datetime | None, datetime | None, int | None]:
        now = utcnow()
        if request.mode == IndexModeEnum.latest_posts:
            return None, None, request.latest_posts_limit
        if request.mode == IndexModeEnum.preset_period:
            since_map = {
                IndexPeriodPresetEnum.day: now - timedelta(days=1),
                IndexPeriodPresetEnum.week: now - timedelta(weeks=1),
                IndexPeriodPresetEnum.month: now - timedelta(days=30),
                IndexPeriodPresetEnum.three_months: now - timedelta(days=90),
                IndexPeriodPresetEnum.six_months: now - timedelta(days=180),
                IndexPeriodPresetEnum.year: now - timedelta(days=365),
            }
            return since_map[request.period_preset], now, None
        if request.mode == IndexModeEnum.custom_period:
            return request.period_from, request.period_to, None
        return None, None, None

    def _fetch_posts_with_cache(self, provider, source, since: datetime | None, until: datetime | None, posts_limit: int | None):
        cache_key = posts_cache_key(str(source.id), since, until, posts_limit)
        cached = load_posts(cache_key)
        if cached is not None:
            logger.info("Posts cache hit for source=%s", source.id)
            return cached

        posts = provider.fetch_posts(source, since=since, until=until, limit=posts_limit)
        save_posts(cache_key, posts)
        return posts

    def _fetch_comments_with_cache(self, provider, source, post):
        cache_key = comments_cache_key(str(source.id), post.external_post_id)
        cached = load_comments(cache_key)
        if cached is not None:
            logger.info("Comments cache hit for source=%s post=%s", source.id, post.external_post_id)
            return cached

        comments = provider.fetch_comments(source, post)
        save_comments(cache_key, comments)
        return comments
