from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class ProjectResponse(ORMModel):
    id: UUID
    user_id: UUID | None
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


class ProjectStats(BaseModel):
    total_sources: int = 0
    total_posts: int = 0
    total_comments: int = 0


class ProjectDetail(ProjectResponse):
    stats: ProjectStats
