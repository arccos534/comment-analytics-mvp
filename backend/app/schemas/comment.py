from datetime import datetime
from uuid import UUID

from app.schemas.common import ORMModel


class CommentResponse(ORMModel):
    id: UUID
    post_id: UUID
    external_comment_id: str
    parent_comment_id: UUID | None
    author_name: str | None
    text: str
    language: str | None
    created_at: datetime
    likes_count: int
    reply_count: int
