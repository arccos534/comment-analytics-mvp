from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.source import (
    SourceBulkCreateResponse,
    SourceCreateRequest,
    SourceResponse,
    SourceValidateRequest,
    SourceValidationResult,
)
from app.services.source_service import SourceService

router = APIRouter(tags=["sources"])


@router.get("/projects/{project_id}/sources", response_model=list[SourceResponse])
def list_sources(project_id: UUID, db: Session = Depends(get_db)) -> list[SourceResponse]:
    return SourceService(db).list_project_sources(project_id)


@router.post("/projects/{project_id}/sources", response_model=SourceBulkCreateResponse, status_code=status.HTTP_201_CREATED)
def add_sources(project_id: UUID, payload: SourceCreateRequest, db: Session = Depends(get_db)) -> SourceBulkCreateResponse:
    service = SourceService(db)
    if not service.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return service.add_sources(project_id, payload.urls)


@router.post("/sources/validate", response_model=list[SourceValidationResult])
def validate_sources(payload: SourceValidateRequest, db: Session = Depends(get_db)) -> list[SourceValidationResult]:
    return SourceService(db).validate_urls(payload.urls)
