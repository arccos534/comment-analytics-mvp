from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["ingestion"])


@router.post("/projects/{project_id}/index", status_code=status.HTTP_202_ACCEPTED)
def start_indexing(project_id: UUID, db: Session = Depends(get_db)) -> dict[str, str]:
    service = IngestionService(db)
    if not service.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    task_id = service.enqueue_project_index(project_id)
    return {"status": "queued", "task_id": task_id}


@router.get("/projects/{project_id}/index-status")
def get_index_status(project_id: UUID, db: Session = Depends(get_db)) -> dict:
    service = IngestionService(db)
    if not service.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return service.get_project_index_status(project_id)
