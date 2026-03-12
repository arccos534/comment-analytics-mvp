from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.post import PostResponse
from app.services.project_service import ProjectService

router = APIRouter(tags=["posts"])


@router.get("/projects/{project_id}/posts", response_model=list[PostResponse])
def list_posts(project_id: UUID, db: Session = Depends(get_db)) -> list[PostResponse]:
    return ProjectService(db).list_posts(project_id)
