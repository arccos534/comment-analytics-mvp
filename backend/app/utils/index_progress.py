from __future__ import annotations

from datetime import datetime
from hashlib import sha256

import orjson
from redis import Redis

from app.core.config import get_settings

_redis_client: Redis | None = None


def _get_client() -> Redis | None:
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    settings = get_settings()
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=False)
        client.ping()
        _redis_client = client
    except Exception:
        _redis_client = None
    return _redis_client


def _progress_key(project_id: str) -> str:
    digest = sha256(project_id.encode("utf-8")).hexdigest()
    return f"comment-analytics:index-progress:{digest}"


def _serialize(value: dict) -> bytes:
    return orjson.dumps(value)


def _deserialize(raw: bytes) -> dict:
    return orjson.loads(raw)


def _ttl_seconds() -> int:
    # Keep progress state slightly longer than ingestion cache so the UI
    # can still show the completed bar shortly after the run finishes.
    return max(get_settings().ingestion_cache_ttl_seconds, 3600)


def init_project_progress(project_id: str, total_sources: int) -> None:
    client = _get_client()
    if client is None:
        return
    payload = {
        "project_id": project_id,
        "total_sources": total_sources,
        "completed_sources": 0,
        "current_source_index": 0,
        "current_source_title": None,
        "current_source_id": None,
        "processed_posts": 0,
        "total_posts": 0,
        "started_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "finished_at": None,
    }
    client.setex(_progress_key(project_id), _ttl_seconds(), _serialize(payload))


def get_project_progress(project_id: str) -> dict | None:
    client = _get_client()
    if client is None:
        return None
    raw = client.get(_progress_key(project_id))
    if not raw:
        return None
    return _deserialize(raw)


def update_project_progress(project_id: str, **fields) -> None:
    client = _get_client()
    if client is None:
        return
    payload = get_project_progress(project_id) or {"project_id": project_id}
    payload.update(fields)
    payload["updated_at"] = datetime.utcnow().isoformat()
    client.setex(_progress_key(project_id), _ttl_seconds(), _serialize(payload))


def start_source_progress(project_id: str, source_id: str, source_title: str | None, source_index: int) -> None:
    update_project_progress(
        project_id,
        current_source_id=source_id,
        current_source_title=source_title,
        current_source_index=source_index,
        processed_posts=0,
        total_posts=0,
        finished_at=None,
    )


def set_source_total_posts(project_id: str, total_posts: int) -> None:
    update_project_progress(project_id, total_posts=total_posts)


def set_source_processed_posts(project_id: str, processed_posts: int) -> None:
    update_project_progress(project_id, processed_posts=processed_posts)


def finish_source_progress(project_id: str) -> None:
    payload = get_project_progress(project_id)
    if payload is None:
        return
    completed = int(payload.get("completed_sources", 0)) + 1
    total_sources = int(payload.get("total_sources", 0))
    update_project_progress(
        project_id,
        completed_sources=completed,
        processed_posts=int(payload.get("total_posts", 0)),
        finished_at=datetime.utcnow().isoformat() if completed >= total_sources and total_sources else None,
    )


def clear_current_source(project_id: str) -> None:
    update_project_progress(
        project_id,
        current_source_id=None,
        current_source_title=None,
        current_source_index=0,
        processed_posts=0,
        total_posts=0,
    )


def clear_project_progress(project_id: str) -> None:
    client = _get_client()
    if client is None:
        return
    client.delete(_progress_key(project_id))


def build_progress_summary(project_id: str) -> dict | None:
    payload = get_project_progress(project_id)
    if payload is None:
        return None

    total_sources = max(int(payload.get("total_sources", 0)), 0)
    completed_sources = max(int(payload.get("completed_sources", 0)), 0)
    processed_posts = max(int(payload.get("processed_posts", 0)), 0)
    total_posts = max(int(payload.get("total_posts", 0)), 0)

    current_fraction = 0.0
    if total_posts > 0:
        current_fraction = min(processed_posts / total_posts, 1.0)

    current_source_percent = round(max(0.0, min(current_fraction * 100, 100.0)), 1)
    if total_sources > 0:
        overall_percent = round(max(0.0, min(((completed_sources + current_fraction) / total_sources) * 100, 100.0)), 1)
    else:
        overall_percent = 0.0

    current_label = None
    if payload.get("current_source_title"):
        current_label = payload["current_source_title"]

    posts_label = None
    if total_posts > 0:
        posts_label = f"{processed_posts}/{total_posts} posts"

    return {
        "percent": current_source_percent,
        "overall_percent": overall_percent,
        "current_source_title": current_label,
        "current_source_index": int(payload.get("current_source_index", 0) or 0),
        "total_sources": total_sources,
        "completed_sources": completed_sources,
        "processed_posts": processed_posts,
        "total_posts": total_posts,
        "posts_label": posts_label,
        "updated_at": payload.get("updated_at"),
        "finished_at": payload.get("finished_at"),
    }
