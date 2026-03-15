from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source import Source


class SourceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_by_project(self, project_id: UUID) -> list[Source]:
        return list(self.db.scalars(select(Source).where(Source.project_id == project_id).order_by(Source.created_at.desc())))

    def get(self, source_id: UUID) -> Source | None:
        return self.db.get(Source, source_id)

    def exists(self, source_id: UUID) -> bool:
        return self.db.scalar(select(Source.id).where(Source.id == source_id)) is not None

    def get_by_project_and_url(self, project_id: UUID, source_url: str) -> Source | None:
        return self.db.scalar(
            select(Source).where(Source.project_id == project_id, Source.source_url == source_url)
        )

    def create(self, source: Source) -> Source:
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def save_many(self, sources: list[Source]) -> list[Source]:
        self.db.add_all(sources)
        self.db.commit()
        for source in sources:
            self.db.refresh(source)
        return sources

    def update(self, source: Source) -> Source:
        self.db.add(source)
        self.db.commit()
        self.db.refresh(source)
        return source

    def delete(self, source_id: UUID) -> bool:
        source = self.get(source_id)
        if not source:
            return False
        self.db.delete(source)
        self.db.commit()
        return True
