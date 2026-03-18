from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AnalysisRunStatusEnum, PlatformEnum
from app.schemas.common import ORMModel


class AnalysisCreateRequest(BaseModel):
    prompt_text: str = Field(min_length=1)
    theme: str | None = None
    keywords: list[str] = Field(default_factory=list)
    analysis_mode_override: str | None = None
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
    relevant_comments_count: int | None = None
    likes_count: int | None = None
    reposts_count: int | None = None


class ReportSchema(BaseModel):
    model_config = ConfigDict(extra="allow")

    meta: dict = Field(default_factory=dict)
    stats: dict = Field(default_factory=dict)
    sentiment: dict = Field(default_factory=dict)
    topics: list[TopicItem] = Field(default_factory=list)
    insights: dict = Field(default_factory=dict)
    examples: dict = Field(default_factory=dict)
    posts: dict = Field(default_factory=dict)
    sources: dict = Field(default_factory=dict)
    summary: dict = Field(default_factory=dict)


class ReportSnapshotResponse(ORMModel):
    id: UUID
    analysis_run_id: UUID
    report_json: ReportSchema
    summary_text: str | None
    created_at: datetime


class SavedReportItem(BaseModel):
    analysis_run_id: UUID
    title: str
    created_at: datetime


class ProjectReportsTreeItem(BaseModel):
    project_id: UUID
    project_name: str
    reports: list[SavedReportItem]
