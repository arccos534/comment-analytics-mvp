from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.analytics import AnalysisCreateRequest, AnalysisRunResponse, ProjectReportsTreeItem, ReportSnapshotResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.post("/projects/{project_id}/analyze", response_model=AnalysisRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_analysis(
    project_id: UUID,
    payload: AnalysisCreateRequest,
    db: Session = Depends(get_db),
) -> AnalysisRunResponse:
    service = AnalyticsService(db)
    if not service.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return service.create_and_enqueue_run(project_id, payload)


@router.post("/projects/{project_id}/active-analysis-run", response_model=AnalysisRunResponse | None)
def find_active_analysis_run(
    project_id: UUID,
    payload: AnalysisCreateRequest,
    db: Session = Depends(get_db),
) -> AnalysisRunResponse | None:
    service = AnalyticsService(db)
    if not service.project_exists(project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return service.find_matching_active_run(project_id, payload)


@router.get("/analysis-runs/{analysis_run_id}", response_model=AnalysisRunResponse)
def get_analysis_run(analysis_run_id: UUID, db: Session = Depends(get_db)) -> AnalysisRunResponse:
    run = AnalyticsService(db).get_run(analysis_run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    return run


@router.get("/analysis-runs/{analysis_run_id}/report", response_model=ReportSnapshotResponse)
def get_report(analysis_run_id: UUID, db: Session = Depends(get_db)) -> ReportSnapshotResponse:
    report = AnalyticsService(db).get_report(analysis_run_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@router.delete("/analysis-runs/{analysis_run_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(analysis_run_id: UUID, db: Session = Depends(get_db)) -> Response:
    deleted = AnalyticsService(db).delete_report(analysis_run_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis run not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/reports-tree", response_model=list[ProjectReportsTreeItem])
def list_reports_tree(db: Session = Depends(get_db)) -> list[ProjectReportsTreeItem]:
    return AnalyticsService(db).list_reports_tree()
