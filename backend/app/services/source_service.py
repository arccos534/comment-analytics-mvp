from dataclasses import asdict
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.enums import SourceStatusEnum
from app.models.source import Source
from app.providers.factory import get_provider
from app.repositories.project_repository import ProjectRepository
from app.repositories.source_repository import SourceRepository
from app.schemas.source import SourceBulkCreateResponse, SourceValidationResult
from app.utils.index_progress import clear_current_source, clear_project_progress
from app.utils.validators import detect_platform_and_type, split_urls


class SourceService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.sources = SourceRepository(db)

    def project_exists(self, project_id: UUID) -> bool:
        return self.projects.exists(project_id)

    def list_project_sources(self, project_id: UUID):
        return self.sources.list_by_project(project_id)

    def delete_source(self, source_id: UUID) -> bool:
        source = self.sources.get(source_id)
        if not source:
            return False
        if source.status == SourceStatusEnum.indexing:
            clear_current_source(str(source.project_id))
            remaining_sources = [
                item
                for item in self.sources.list_by_project(source.project_id)
                if item.id != source.id and item.status in {SourceStatusEnum.pending, SourceStatusEnum.indexing}
            ]
            if not remaining_sources:
                clear_project_progress(str(source.project_id))
        return self.sources.delete(source_id)

    def validate_urls(self, raw_urls: list[str]) -> list[SourceValidationResult]:
        results: list[SourceValidationResult] = []
        for url in split_urls(raw_urls):
            base_result = detect_platform_and_type(url)
            if base_result.platform:
                provider = get_provider(base_result.platform)
                base_result = provider.validate_source(url)
            results.append(SourceValidationResult.model_validate(asdict(base_result)))
        return results

    def add_sources(self, project_id: UUID, raw_urls: list[str]) -> SourceBulkCreateResponse:
        created: list[Source] = []
        skipped: list[SourceValidationResult] = []
        seen_urls: set[str] = set()
        for result in self.validate_urls(raw_urls):
            if not result.is_valid or not result.can_save or not result.normalized_url:
                skipped.append(result)
                continue
            if result.normalized_url in seen_urls or self.sources.get_by_project_and_url(project_id, result.normalized_url):
                payload = result.model_dump()
                payload["can_save"] = False
                payload["reason"] = "Source already exists in project"
                skipped.append(SourceValidationResult(**payload))
                continue
            seen_urls.add(result.normalized_url)
            source = Source(
                project_id=project_id,
                platform=result.platform,
                source_type=result.source_type,
                source_url=result.normalized_url,
                external_source_id=result.external_source_id,
                title=result.title,
                status=SourceStatusEnum.pending,
            )
            created.append(source)

        if created:
            created = self.sources.save_many(created)
        return SourceBulkCreateResponse(created=created, skipped=skipped)
