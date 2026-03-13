from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

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


class IndexModeEnum(str, Enum):
    full = "full"
    latest_posts = "latest_posts"
    preset_period = "preset_period"
    custom_period = "custom_period"


class IndexPeriodPresetEnum(str, Enum):
    day = "day"
    week = "week"
    month = "month"
    three_months = "three_months"
    six_months = "six_months"
    year = "year"


class IndexRequest(BaseModel):
    mode: IndexModeEnum = IndexModeEnum.full
    latest_posts_limit: int | None = Field(default=None, ge=1, le=5000)
    period_preset: IndexPeriodPresetEnum | None = None
    period_from: datetime | None = None
    period_to: datetime | None = None

    @model_validator(mode="after")
    def validate_mode_requirements(self) -> "IndexRequest":
        if self.mode == IndexModeEnum.latest_posts and not self.latest_posts_limit:
            raise ValueError("latest_posts_limit is required for latest_posts mode")
        if self.mode == IndexModeEnum.preset_period and not self.period_preset:
            raise ValueError("period_preset is required for preset_period mode")
        if self.mode == IndexModeEnum.custom_period and not self.period_from:
            raise ValueError("period_from is required for custom_period mode")
        if self.period_from and self.period_to and self.period_from > self.period_to:
            raise ValueError("period_from must be earlier than period_to")
        return self
