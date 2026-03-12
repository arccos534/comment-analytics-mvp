from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.post import Post
from app.models.project import Project
from app.models.source import Source
from app.schemas.project import ProjectCreate, ProjectStats


class ProjectRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Project]:
        return list(self.db.scalars(select(Project).order_by(Project.created_at.desc())))

    def get(self, project_id: UUID) -> Project | None:
        return self.db.get(Project, project_id)

    def exists(self, project_id: UUID) -> bool:
        return self.get(project_id) is not None

    def create(self, payload: ProjectCreate) -> Project:
        project = Project(name=payload.name, description=payload.description)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_stats(self, project_id: UUID) -> ProjectStats:
        source_count = self.db.scalar(select(func.count(Source.id)).where(Source.project_id == project_id)) or 0
        post_count = self.db.scalar(
            select(func.count(Post.id)).join(Source, Post.source_id == Source.id).where(Source.project_id == project_id)
        ) or 0
        comment_count = self.db.scalar(
            select(func.count(Comment.id))
            .join(Post, Comment.post_id == Post.id)
            .join(Source, Post.source_id == Source.id)
            .where(Source.project_id == project_id)
        ) or 0
        return ProjectStats(total_sources=source_count, total_posts=post_count, total_comments=comment_count)
