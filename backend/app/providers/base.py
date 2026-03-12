from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime

from app.models.enums import PlatformEnum, SourceTypeEnum


@dataclass(slots=True)
class ProviderValidationResult:
    url: str
    normalized_url: str | None
    platform: PlatformEnum | None
    source_type: SourceTypeEnum | None
    is_valid: bool
    can_save: bool
    reason: str | None = None
    external_source_id: str | None = None
    title: str | None = None


@dataclass(slots=True)
class NormalizedPost:
    external_post_id: str
    post_url: str
    post_text: str | None
    post_date: datetime
    likes_count: int = 0
    views_count: int = 0
    comments_count: int = 0
    raw_payload: dict | None = None


@dataclass(slots=True)
class NormalizedComment:
    external_comment_id: str
    text: str
    created_at: datetime
    parent_external_comment_id: str | None = None
    author_external_id: str | None = None
    author_name: str | None = None
    language: str | None = "ru"
    likes_count: int = 0
    reply_count: int = 0
    raw_payload: dict | None = None


@dataclass(slots=True)
class ProviderContext:
    demo_mode: bool = True
    metadata: dict = field(default_factory=dict)


class ProviderError(Exception):
    """Base provider error."""


class ProviderConfigurationError(ProviderError):
    """Raised when provider credentials are missing or invalid."""


class ProviderRequestError(ProviderError):
    """Raised when remote provider request fails."""


class BaseProvider(ABC):
    platform: PlatformEnum

    def __init__(self, context: ProviderContext | None = None) -> None:
        self.context = context or ProviderContext()

    @abstractmethod
    def validate_source(self, url: str) -> ProviderValidationResult: ...

    @abstractmethod
    def fetch_posts(self, source, since: datetime | None = None) -> list[NormalizedPost]: ...

    @abstractmethod
    def fetch_comments(self, source, post: NormalizedPost) -> list[NormalizedComment]: ...
