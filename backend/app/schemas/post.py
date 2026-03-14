from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class PostResponse(ORMModel):
    id: UUID
    source_id: UUID
    external_post_id: str
    post_url: str
    post_text: str | None
    post_date: datetime
    likes_count: int
    reposts_count: int
    views_count: int
    comments_count: int
