from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.comment import CommentResponse
from app.services.project_service import ProjectService

router = APIRouter(tags=["comments"])


@router.get("/projects/{project_id}/comments", response_model=list[CommentResponse])
def list_comments(project_id: UUID, db: Session = Depends(get_db)) -> list[CommentResponse]:
    return ProjectService(db).list_comments(project_id)
