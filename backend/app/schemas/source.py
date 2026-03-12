from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.models.enums import PlatformEnum, SourceStatusEnum, SourceTypeEnum
from app.schemas.common import ORMModel


class SourceValidateRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)


class SourceValidationResult(BaseModel):
    url: str
    normalized_url: str | None = None
    platform: PlatformEnum | None = None
    source_type: SourceTypeEnum | None = None
    is_valid: bool
    can_save: bool
    reason: str | None = None
    external_source_id: str | None = None
    title: str | None = None


class SourceCreateItem(BaseModel):
    url: str = Field(min_length=1)


class SourceCreateRequest(BaseModel):
    urls: list[str] = Field(default_factory=list)


class SourceResponse(ORMModel):
    id: UUID
    project_id: UUID
    platform: PlatformEnum
    source_type: SourceTypeEnum
    source_url: str
    external_source_id: str | None
    title: str | None
    status: SourceStatusEnum
    last_indexed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SourceBulkCreateResponse(BaseModel):
    created: list[SourceResponse]
    skipped: list[SourceValidationResult]
