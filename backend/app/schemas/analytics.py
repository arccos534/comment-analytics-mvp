from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import AnalysisRunStatusEnum, PlatformEnum
from app.schemas.common import ORMModel


class AnalysisCreateRequest(BaseModel):
    prompt_text: str = Field(min_length=1)
    theme: str | None = None
    keywords: list[str] = Field(default_factory=list)
    period_from: datetime | None = None
    period_to: datetime | None = None
    platforms: list[PlatformEnum] = Field(default_factory=list)
    source_ids: list[UUID] = Field(default_factory=list)


class AnalysisRunResponse(ORMModel):
    id: UUID
    project_id: UUID
    prompt_text: str
    theme: str | None
    keywords_json: list[str] | None
    period_from: datetime | None
    period_to: datetime | None
    filters_json: dict | None
    status: AnalysisRunStatusEnum
    created_at: datetime
    finished_at: datetime | None


class TopicItem(BaseModel):
    name: str
    count: int
    share: float


class ReportExampleComment(BaseModel):
    comment_id: UUID | None = None
    text: str
    sentiment: str | None = None
    relevance_score: float | None = None
    post_url: str | None = None


class ReportPostItem(BaseModel):
    post_id: UUID | None = None
    post_url: str
    post_text: str | None = None
    score: float
    comments_count: int


class ReportSchema(BaseModel):
    meta: dict
    stats: dict
    sentiment: dict
    topics: list[TopicItem]
    insights: dict
    examples: dict
    posts: dict
    summary: dict


class ReportSnapshotResponse(ORMModel):
    id: UUID
    analysis_run_id: UUID
    report_json: ReportSchema
    summary_text: str | None
    created_at: datetime
