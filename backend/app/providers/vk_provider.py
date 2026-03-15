from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from app.core.config import get_settings
from app.models.enums import PlatformEnum, SourceTypeEnum
from app.providers.base import (
    BaseProvider,
    NormalizedComment,
    NormalizedPost,
    ProviderConfigurationError,
    ProviderRequestError,
    ProviderValidationResult,
)
from app.utils.dates import default_since, utcnow
from app.utils.validators import detect_platform_and_type


class VkProvider(BaseProvider):
    platform = PlatformEnum.vk

    def __init__(self, context=None) -> None:
        super().__init__(context=context)
        self.settings = get_settings()

    def validate_source(self, url: str) -> ProviderValidationResult:
        result = detect_platform_and_type(url)
        if result.platform != self.platform:
            result.is_valid = False
            result.can_save = False
            result.reason = "URL does not belong to VK"
            return result

        if self.context.demo_mode:
            return result

        try:
            return self._validate_live(result)
        except (ProviderConfigurationError, ProviderRequestError) as exc:
            result.is_valid = False
            result.can_save = False
            result.reason = str(exc)
            return result

    def fetch_posts(self, source, since=None, until=None, limit=None) -> list[NormalizedPost]:
        if self.context.demo_mode:
            return self._fetch_demo_posts(source, since=since)
        return self._fetch_posts_live(source, since=since, until=until, limit=limit)

    def fetch_comments(self, source, post: NormalizedPost) -> list[NormalizedComment]:
        if self.context.demo_mode:
            return self._fetch_demo_comments(source, post)
        return self._fetch_comments_live(source, post)

    def _validate_live(self, result: ProviderValidationResult) -> ProviderValidationResult:
        self._ensure_token()
        with self._make_http_client() as client:
            if result.source_type == SourceTypeEnum.community:
                group = self._resolve_group(result.external_source_id or result.normalized_url or result.url, client=client)
                result.external_source_id = str(-abs(group["id"]))
                result.title = group["name"]
                result.subscriber_count = int(group.get("members_count", 0) or 0) or None
                return result

            owner_id, post_id = self._parse_vk_post_id(result.external_source_id)
            post = self._api_call("wall.getById", {"posts": f"wall{owner_id}_{post_id}"}, client=client)[0]
            result.external_source_id = f"{owner_id}_{post_id}"
            result.title = self._build_post_title(post)
            return result

    def _fetch_posts_live(
        self,
        source,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[NormalizedPost]:
        self._ensure_token()
        since_dt = since.astimezone(UTC) if since else None
        until_dt = until.astimezone(UTC) if until else None
        with self._make_http_client() as client:
            if source.source_type == SourceTypeEnum.post:
                owner_id, post_id = self._parse_vk_post_id(source.external_source_id)
                items = self._api_call("wall.getById", {"posts": f"wall{owner_id}_{post_id}"}, client=client)
            else:
                owner_id = int(source.external_source_id)
                items = self._fetch_all_wall_posts(owner_id, since_dt, until_dt, limit, client=client)

        posts: list[NormalizedPost] = []
        for item in items:
            post_date = datetime.fromtimestamp(item["date"], tz=UTC)
            if since_dt and post_date <= since_dt:
                continue
            if until_dt and post_date > until_dt:
                continue
            posts.append(self._normalize_post(item))
        return posts

    def _fetch_comments_live(self, source, post: NormalizedPost) -> list[NormalizedComment]:
        self._ensure_token()
        owner_id, post_id = self._owner_and_post_id(source, post)
        with self._make_http_client() as client:
            items, profiles, groups = self._fetch_all_post_comments(owner_id, post_id, client=client)

        comments: list[NormalizedComment] = []
        for item in items:
            text = (item.get("text") or "").strip()
            if not text:
                continue
            from_id = item.get("from_id")
            author_name = self._resolve_author_name(from_id, profiles, groups)
            comments.append(
                NormalizedComment(
                    external_comment_id=str(item["id"]),
                    text=text,
                    created_at=datetime.fromtimestamp(item["date"], tz=UTC),
                    parent_external_comment_id=str(item["reply_to_comment"]) if item.get("reply_to_comment") else None,
                    author_external_id=str(from_id) if from_id is not None else None,
                    author_name=author_name,
                    language="ru",
                    likes_count=item.get("likes", {}).get("count", 0),
                    reply_count=item.get("thread", {}).get("count", 0),
                    raw_payload={"provider": "vk", "demo": False, "comment_id": item["id"]},
                )
            )
        return comments

    def _fetch_demo_posts(self, source, since=None) -> list[NormalizedPost]:
        since_dt = since or default_since()
        base_date = max(since_dt, utcnow() - timedelta(days=21))
        slug = source.external_source_id or "demo_community"
        return [
            NormalizedPost(
                external_post_id=f"{slug}-201",
                post_url=f"{source.source_url}/w1" if source.source_type.value == "community" else source.source_url,
                post_text="Пост о новых функциях, стоимости и ожиданиях пользователей.",
                post_date=base_date + timedelta(days=5),
                likes_count=84,
                reposts_count=11,
                views_count=2200,
                comments_count=5,
                raw_payload={"provider": "vk", "demo": True},
            ),
            NormalizedPost(
                external_post_id=f"{slug}-202",
                post_url=f"{source.source_url}/w2" if source.source_type.value == "community" else source.source_url,
                post_text="Пост о стабильности, багфиксе и удобстве интерфейса.",
                post_date=base_date + timedelta(days=11),
                likes_count=52,
                reposts_count=6,
                views_count=1800,
                comments_count=5,
                raw_payload={"provider": "vk", "demo": True},
            ),
        ]

    def _fetch_demo_comments(self, source, post: NormalizedPost) -> list[NormalizedComment]:
        base_time = post.post_date + timedelta(hours=1)
        texts = [
            "Интерфейс стал удобнее, спасибо за обновление.",
            "Нравится, что стало меньше багов и быстрее загружается.",
            "Стоимость все еще кусается, это главный минус.",
            "Хотелось бы более стабильную модерацию комментариев.",
            "В целом продукт полезный, но не хватает гибких тарифов.",
        ]
        return [
            NormalizedComment(
                external_comment_id=f"{post.external_post_id}-vk-{index}",
                text=text,
                created_at=base_time + timedelta(minutes=index * 11),
                author_external_id=f"vk-user-{index}",
                author_name=f"vk_user_{index}",
                likes_count=index,
                reply_count=max(0, index - 2),
                raw_payload={"provider": "vk", "demo": True, "source_id": str(source.id)},
            )
            for index, text in enumerate(texts, start=1)
        ]

    def _normalize_post(self, item: dict[str, Any]) -> NormalizedPost:
        owner_id = item["owner_id"]
        post_id = item["id"]
        return NormalizedPost(
            external_post_id=f"{owner_id}_{post_id}",
            post_url=f"https://vk.com/wall{owner_id}_{post_id}",
            post_text=item.get("text") or None,
            post_date=datetime.fromtimestamp(item["date"], tz=UTC),
            likes_count=item.get("likes", {}).get("count", 0),
            reposts_count=item.get("reposts", {}).get("count", item.get("shares", {}).get("count", 0)),
            views_count=item.get("views", {}).get("count", 0),
            comments_count=item.get("comments", {}).get("count", 0),
            raw_payload={"provider": "vk", "demo": False, "owner_id": owner_id, "post_id": post_id},
        )

    @contextmanager
    def _make_http_client(self):
        with httpx.Client(timeout=self.settings.provider_http_timeout_seconds) as client:
            yield client

    def _resolve_group(self, slug: str, client: httpx.Client | None = None) -> dict[str, Any]:
        resolved = self._api_call("utils.resolveScreenName", {"screen_name": slug}, client=client)
        if not resolved or resolved.get("type") not in {"group", "page", "event"}:
            raise ProviderRequestError("VK source is not a public community")
        groups = self._api_call(
            "groups.getById",
            {"group_ids": resolved["object_id"], "fields": "members_count"},
            client=client,
        )
        if isinstance(groups, dict) and "groups" in groups:
            groups = groups["groups"]
        if isinstance(groups, dict):
            groups = [groups]
        if not groups:
            raise ProviderRequestError("VK group metadata not found")
        return groups[0]

    def _api_call(self, method: str, params: dict[str, Any], client: httpx.Client | None = None) -> Any:
        self._ensure_token()
        query = {
            **params,
            "access_token": self.settings.vk_api_token,
            "v": self.settings.vk_api_version,
        }
        attempts = 5
        if client is None:
            with self._make_http_client() as managed_client:
                return self._api_call(method, params, client=managed_client)
        else:
            for attempt in range(attempts):
                response = client.get(f"https://api.vk.com/method/{method}", params=query)
                response.raise_for_status()
                payload = response.json()
                if not payload.get("error"):
                    return payload["response"]

                error = payload["error"]
                error_code = error.get("error_code")
                if error_code == 6 and attempt < attempts - 1:
                    time.sleep(0.35 * (attempt + 1))
                    continue
                raise ProviderRequestError(f"VK API {method} failed: {error.get('error_msg', 'unknown error')}")

        raise ProviderRequestError(f"VK API {method} failed after retries")

    def _ensure_token(self) -> None:
        if not self.settings.vk_api_token:
            raise ProviderConfigurationError("VK live ingestion requires VK_API_TOKEN")

    def _parse_vk_post_id(self, external_source_id: str | None) -> tuple[int, int]:
        if not external_source_id or "_" not in external_source_id:
            raise ProviderRequestError("VK post source is malformed")
        owner_id, post_id = external_source_id.split("_", maxsplit=1)
        return int(owner_id), int(post_id)

    def _owner_and_post_id(self, source, post: NormalizedPost) -> tuple[int, int]:
        raw_payload = post.raw_payload or {}
        if raw_payload.get("owner_id") is not None and raw_payload.get("post_id") is not None:
            return int(raw_payload["owner_id"]), int(raw_payload["post_id"])
        if "_" in post.external_post_id:
            return self._parse_vk_post_id(post.external_post_id)
        if source.source_type == SourceTypeEnum.post:
            return self._parse_vk_post_id(source.external_source_id)
        raise ProviderRequestError("VK post metadata is incomplete")

    def _resolve_author_name(
        self,
        from_id: int | None,
        profiles: dict[int, dict[str, Any]],
        groups: dict[int, dict[str, Any]],
    ) -> str | None:
        if from_id is None:
            return None
        if from_id > 0:
            profile = profiles.get(from_id, {})
            first_name = profile.get("first_name", "")
            last_name = profile.get("last_name", "")
            return f"{first_name} {last_name}".strip() or None
        group = groups.get(abs(from_id), {})
        return group.get("name")

    def _build_post_title(self, post: dict[str, Any]) -> str:
        text = (post.get("text") or "").strip()
        if text:
            return text[:120]
        return f"VK post wall{post['owner_id']}_{post['id']}"

    def _fetch_all_wall_posts(
        self,
        owner_id: int,
        since_dt: datetime | None,
        until_dt: datetime | None,
        limit: int | None,
        client: httpx.Client,
    ) -> list[dict[str, Any]]:
        page_size = max(1, min(self.settings.ingestion_batch_size, 100))
        offset = 0
        items: list[dict[str, Any]] = []
        should_stop = False

        while not should_stop:
            response = self._api_call(
                "wall.get",
                {
                    "owner_id": owner_id,
                    "count": page_size,
                    "offset": offset,
                    "filter": "owner",
                },
                client=client,
            )
            batch = response.get("items", [])
            if not batch:
                break

            for item in batch:
                post_date = datetime.fromtimestamp(item["date"], tz=UTC)
                if until_dt and post_date > until_dt:
                    continue
                if since_dt:
                    if post_date <= since_dt:
                        should_stop = True
                        break
                items.append(item)
                if limit and len(items) >= limit:
                    should_stop = True
                    break

            offset += len(batch)
            if len(batch) < page_size:
                break

        return items

    def _fetch_all_post_comments(
        self,
        owner_id: int,
        post_id: int,
        client: httpx.Client,
    ) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
        page_size = max(1, min(self.settings.ingestion_batch_size, 100))
        offset = 0
        items: list[dict[str, Any]] = []
        profiles: dict[int, dict[str, Any]] = {}
        groups: dict[int, dict[str, Any]] = {}

        while True:
            response = self._api_call(
                "wall.getComments",
                {
                    "owner_id": owner_id,
                    "post_id": post_id,
                    "count": page_size,
                    "offset": offset,
                    "sort": "asc",
                    "extended": 1,
                    "thread_items_count": 10,
                },
                client=client,
            )
            batch = response.get("items", [])
            if not batch:
                break

            for profile in response.get("profiles", []):
                profiles[profile["id"]] = profile
            for group in response.get("groups", []):
                groups[group["id"]] = group

            for item in batch:
                items.append(item)
                thread = item.get("thread", {})
                thread_items = thread.get("items", []) or []
                items.extend(thread_items)

                if thread.get("count", 0) > len(thread_items):
                    nested_items, nested_profiles, nested_groups = self._fetch_comment_thread(
                        owner_id,
                        post_id,
                        item["id"],
                        initial_offset=len(thread_items),
                        client=client,
                    )
                    items.extend(nested_items)
                    profiles.update(nested_profiles)
                    groups.update(nested_groups)

            offset += len(batch)
            if len(batch) < page_size:
                break

        return items, profiles, groups

    def _fetch_comment_thread(
        self,
        owner_id: int,
        post_id: int,
        comment_id: int,
        initial_offset: int = 0,
        client: httpx.Client | None = None,
    ) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], dict[int, dict[str, Any]]]:
        page_size = max(1, min(self.settings.ingestion_batch_size, 100))
        offset = initial_offset
        items: list[dict[str, Any]] = []
        profiles: dict[int, dict[str, Any]] = {}
        groups: dict[int, dict[str, Any]] = {}

        while True:
            response = self._api_call(
                "wall.getComments",
                {
                    "owner_id": owner_id,
                    "post_id": post_id,
                    "comment_id": comment_id,
                    "count": page_size,
                    "offset": offset,
                    "sort": "asc",
                    "extended": 1,
                },
                client=client,
            )
            batch = response.get("items", [])
            if not batch:
                break

            for profile in response.get("profiles", []):
                profiles[profile["id"]] = profile
            for group in response.get("groups", []):
                groups[group["id"]] = group
            items.extend(batch)

            offset += len(batch)
            if len(batch) < page_size:
                break

        return items, profiles, groups
