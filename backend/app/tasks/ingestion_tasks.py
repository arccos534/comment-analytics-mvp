from uuid import UUID

from app.db.session import SessionLocal
from app.services.ingestion_service import IngestionService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.index_project_sources_task")
def index_project_sources_task(project_id: str) -> dict:
    db = SessionLocal()
    try:
        return IngestionService(db).index_project_sources_sync(UUID(project_id))
    finally:
        db.close()


@celery_app.task(name="app.tasks.index_single_source_task")
def index_single_source_task(source_id: str) -> dict:
    db = SessionLocal()
    try:
        return IngestionService(db).index_single_source_sync(UUID(source_id))
    finally:
        db.close()
