from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

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

try:
    from telethon import TelegramClient
    from telethon.errors import ChannelPrivateError, MsgIdInvalidError, RPCError, UsernameInvalidError, UsernameNotOccupiedError
    from telethon.sessions import StringSession
except Exception:  # pragma: no cover
    TelegramClient = None
    StringSession = None
    ChannelPrivateError = MsgIdInvalidError = RPCError = UsernameInvalidError = UsernameNotOccupiedError = Exception


class TelegramProvider(BaseProvider):
    platform = PlatformEnum.telegram

    def __init__(self, context=None) -> None:
        super().__init__(context=context)
        self.settings = get_settings()

    def validate_source(self, url: str) -> ProviderValidationResult:
        result = detect_platform_and_type(url)
        if result.platform != self.platform:
            result.is_valid = False
            result.can_save = False
            result.reason = "URL does not belong to Telegram"
            return result

        if self.context.demo_mode:
            return result

        try:
            return self._run(self._validate_live(url, result))
        except ProviderConfigurationError as exc:
            result.is_valid = False
            result.can_save = False
            result.reason = str(exc)
            return result
        except ProviderRequestError as exc:
            result.is_valid = False
            result.can_save = False
            result.reason = str(exc)
            return result

    def fetch_posts(self, source, since=None, until=None, limit=None) -> list[NormalizedPost]:
        if self.context.demo_mode:
            return self._fetch_demo_posts(source, since=since)
        return self._run(self._fetch_posts_live(source, since=since, until=until, limit=limit))

    def fetch_comments(self, source, post: NormalizedPost) -> list[NormalizedComment]:
        if self.context.demo_mode:
            return self._fetch_demo_comments(source, post)
        return self._run(self._fetch_comments_live(source, post))

    async def _validate_live(self, url: str, result: ProviderValidationResult) -> ProviderValidationResult:
        async with self._make_client() as client:
            if result.source_type == SourceTypeEnum.channel:
                entity = await client.get_entity(result.external_source_id or url)
                result.external_source_id = getattr(entity, "username", None) or result.external_source_id
                result.title = getattr(entity, "title", None) or result.title
                return result

            slug, post_id = self._parse_post_url(result.external_source_id)
            entity = await client.get_entity(slug)
            message = await client.get_messages(entity, ids=post_id)
            if not message:
                raise ProviderRequestError("Telegram post not found")
            result.external_source_id = f"{slug}:{post_id}"
            result.title = f"{getattr(entity, 'title', slug)} post {post_id}"
            return result

    async def _fetch_posts_live(
        self,
        source,
        since: datetime | None = None,
        until: datetime | None = None,
        limit: int | None = None,
    ) -> list[NormalizedPost]:
        since_dt = since.astimezone(UTC) if since else None
        until_dt = until.astimezone(UTC) if until else None
        async with self._make_client() as client:
            if source.source_type == SourceTypeEnum.post:
                slug, post_id = self._parse_post_url(source.external_source_id)
                entity = await client.get_entity(slug)
                message = await client.get_messages(entity, ids=post_id)
                if not message:
                    return []
                if since_dt and message.date and message.date <= since_dt:
                    return []
                if until_dt and message.date and message.date > until_dt:
                    return []
                normalized = self._normalize_post(source, entity, message)
                return [normalized] if normalized else []

            entity = await client.get_entity(source.external_source_id or source.source_url)
            posts: list[NormalizedPost] = []
            async for message in client.iter_messages(entity, limit=None):
                normalized = self._normalize_post(source, entity, message)
                if not normalized:
                    continue
                if until_dt and normalized.post_date > until_dt:
                    continue
                if since_dt and normalized.post_date <= since_dt:
                    break
                posts.append(normalized)
                if limit and len(posts) >= limit:
                    break
            return posts

    async def _fetch_comments_live(self, source, post: NormalizedPost) -> list[NormalizedComment]:
        entity_ref = (post.raw_payload or {}).get("entity_ref") or source.external_source_id or source.source_url
        comments: list[NormalizedComment] = []
        try:
            async with self._make_client() as client:
                entity = await client.get_entity(entity_ref)
                async for message in client.iter_messages(
                    entity,
                    limit=None,
                    reply_to=int(post.external_post_id),
                ):
                    if not getattr(message, "message", None):
                        continue
                    sender = await message.get_sender()
                    comments.append(
                        NormalizedComment(
                            external_comment_id=str(message.id),
                            text=message.message,
                            created_at=message.date,
                            parent_external_comment_id=self._extract_parent_comment_id(message),
                            author_external_id=str(getattr(sender, "id", "")) or None,
                            author_name=self._resolve_sender_name(sender),
                            language="ru",
                            likes_count=0,
                            reply_count=0,
                            raw_payload={
                                "provider": "telegram",
                                "demo": False,
                                "message_id": message.id,
                            },
                        )
                    )
        except (MsgIdInvalidError, ChannelPrivateError):
            return []
        except RPCError as exc:
            raise ProviderRequestError(f"Telegram comments fetch failed: {exc}") from exc
        return comments

    def _fetch_demo_posts(self, source, since=None) -> list[NormalizedPost]:
        since_dt = since or default_since()
        base_date = max(since_dt, utcnow() - timedelta(days=14))
        slug = source.external_source_id or "demo_channel"
        return [
            NormalizedPost(
                external_post_id=f"{slug}-101",
                post_url=f"{source.source_url}/101" if source.source_type.value == "channel" else source.source_url,
                post_text="Новый запуск продукта, обсуждение цены и качества сервиса.",
                post_date=base_date + timedelta(days=3),
                likes_count=0,
                views_count=3400,
                comments_count=4,
                raw_payload={"provider": "telegram", "demo": True, "entity_ref": slug},
            ),
            NormalizedPost(
                external_post_id=f"{slug}-102",
                post_url=f"{source.source_url}/102" if source.source_type.value == "channel" else source.source_url,
                post_text="Обновление доставки, поддержки и скорости ответа команды.",
                post_date=base_date + timedelta(days=7),
                likes_count=0,
                views_count=2800,
                comments_count=4,
                raw_payload={"provider": "telegram", "demo": True, "entity_ref": slug},
            ),
        ]

    def _fetch_demo_comments(self, source, post: NormalizedPost) -> list[NormalizedComment]:
        base_time = post.post_date + timedelta(hours=2)
        texts = [
            "Очень нравится скорость доставки, стало заметно лучше.",
            "Поддержка ответила быстро, приятно видеть такой сервис.",
            "Цена выглядит завышенной, ожидал более доступный тариф.",
            "Иногда качество ответа поддержки скачет, это раздражает.",
        ]
        return [
            NormalizedComment(
                external_comment_id=f"{post.external_post_id}-c{index}",
                text=text,
                created_at=base_time + timedelta(minutes=index * 9),
                author_external_id=f"tg-user-{index}",
                author_name=f"tg_user_{index}",
                likes_count=max(0, 5 - index),
                reply_count=index % 2,
                raw_payload={"provider": "telegram", "demo": True, "source_id": str(source.id)},
            )
            for index, text in enumerate(texts, start=1)
        ]

    def _normalize_post(self, source, entity: Any, message: Any) -> NormalizedPost | None:
        if not getattr(message, "id", None) or not getattr(message, "date", None):
            return None
        if not getattr(message, "message", None) and not getattr(message, "media", None):
            return None

        username = getattr(entity, "username", None) or source.external_source_id or ""
        post_url = source.source_url if source.source_type == SourceTypeEnum.post else f"https://t.me/{username}/{message.id}"
        comments_count = getattr(getattr(message, "replies", None), "replies", 0) or 0
        views_count = getattr(message, "views", None) or 0

        return NormalizedPost(
            external_post_id=str(message.id),
            post_url=post_url,
            post_text=getattr(message, "message", None),
            post_date=message.date,
            likes_count=0,
            views_count=views_count,
            comments_count=comments_count,
            raw_payload={
                "provider": "telegram",
                "demo": False,
                "entity_ref": getattr(entity, "username", None) or getattr(entity, "id", None),
                "message_id": message.id,
            },
        )

    def _make_client(self):
        if not TelegramClient or not StringSession:
            raise ProviderConfigurationError("Telethon is not installed")
        if not self.settings.telegram_api_id or not self.settings.telegram_api_hash or not self.settings.telegram_session_string:
            raise ProviderConfigurationError(
                "Telegram live ingestion requires TELEGRAM_API_ID, TELEGRAM_API_HASH and TELEGRAM_SESSION_STRING"
            )
        return TelegramClient(
            StringSession(self.settings.telegram_session_string),
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
        )

    def _parse_post_url(self, external_source_id: str | None) -> tuple[str, int]:
        if not external_source_id or ":" not in external_source_id:
            raise ProviderRequestError("Telegram post source is malformed")
        slug, post_id = external_source_id.split(":", maxsplit=1)
        return slug, int(post_id)

    def _resolve_sender_name(self, sender: Any) -> str | None:
        if not sender:
            return None
        title = getattr(sender, "title", None)
        if title:
            return title
        username = getattr(sender, "username", None)
        if username:
            return username
        first_name = getattr(sender, "first_name", None) or ""
        last_name = getattr(sender, "last_name", None) or ""
        full_name = f"{first_name} {last_name}".strip()
        return full_name or None

    def _extract_parent_comment_id(self, message: Any) -> str | None:
        reply_to = getattr(message, "reply_to", None)
        reply_to_msg_id = getattr(reply_to, "reply_to_msg_id", None) if reply_to else None
        if not reply_to_msg_id or str(reply_to_msg_id) == str(message.id):
            return None
        return str(reply_to_msg_id)

    def _run(self, coroutine):
        try:
            return asyncio.run(coroutine)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(coroutine)
            finally:
                loop.close()
        except (UsernameInvalidError, UsernameNotOccupiedError, ChannelPrivateError) as exc:
            raise ProviderRequestError(f"Telegram source is unavailable: {exc}") from exc
        except RPCError as exc:
            raise ProviderRequestError(f"Telegram request failed: {exc}") from exc
