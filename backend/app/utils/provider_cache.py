from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from typing import Any

import orjson
from redis import Redis

from app.core.config import get_settings
from app.providers.base import NormalizedComment, NormalizedPost

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


def _make_key(prefix: str, parts: list[str | None]) -> str:
    raw = "|".join(part or "" for part in parts)
    digest = sha256(raw.encode("utf-8")).hexdigest()
    return f"comment-analytics:{prefix}:{digest}"


def _default_serializer(value: Any) -> Any:
    if isinstance(value, datetime):
        return {"__datetime__": value.isoformat()}
    raise TypeError


def _normalize_datetimes(payload: Any) -> Any:
    if isinstance(payload, dict):
        if "__datetime__" in payload:
            return datetime.fromisoformat(payload["__datetime__"])
        return {key: _normalize_datetimes(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_normalize_datetimes(item) for item in payload]
    return payload


def _serialize(value: Any) -> bytes:
    return orjson.dumps(value, default=_default_serializer)


def _deserialize(raw: bytes) -> Any:
    return _normalize_datetimes(orjson.loads(raw))


def posts_cache_key(source_id: str, since: datetime | None, until: datetime | None, limit: int | None) -> str:
    return _make_key(
        "posts",
        [
            source_id,
            since.isoformat() if since else None,
            until.isoformat() if until else None,
            str(limit) if limit is not None else None,
        ],
    )


def comments_cache_key(source_id: str, post_external_id: str) -> str:
    return _make_key("comments", [source_id, post_external_id])


def load_posts(key: str) -> list[NormalizedPost] | None:
    client = _get_client()
    if client is None:
        return None
    raw = client.get(key)
    if not raw:
        return None
    payload = _deserialize(raw)
    return [NormalizedPost(**item) for item in payload]


def save_posts(key: str, posts: list[NormalizedPost]) -> None:
    client = _get_client()
    if client is None:
        return
    ttl = get_settings().ingestion_cache_ttl_seconds
    client.setex(key, ttl, _serialize([asdict(post) for post in posts]))


def load_comments(key: str) -> list[NormalizedComment] | None:
    client = _get_client()
    if client is None:
        return None
    raw = client.get(key)
    if not raw:
        return None
    payload = _deserialize(raw)
    return [NormalizedComment(**item) for item in payload]


def save_comments(key: str, comments: list[NormalizedComment]) -> None:
    client = _get_client()
    if client is None:
        return
    ttl = get_settings().ingestion_cache_ttl_seconds
    client.setex(key, ttl, _serialize([asdict(comment) for comment in comments]))
