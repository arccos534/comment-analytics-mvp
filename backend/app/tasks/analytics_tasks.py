from uuid import UUID

from app.db.session import SessionLocal
from app.services.analytics_service import AnalyticsService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.run_analysis_task")
def run_analysis_task(analysis_run_id: str) -> dict:
    db = SessionLocal()
    try:
        return AnalyticsService(db).execute_run_sync(UUID(analysis_run_id))
    finally:
        db.close()
