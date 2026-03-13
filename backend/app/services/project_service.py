from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectDetail


class ProjectService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.projects = ProjectRepository(db)
        self.posts = PostRepository(db)
        self.comments = CommentRepository(db)

    def list_projects(self):
        return self.projects.list()

    def create_project(self, payload: ProjectCreate):
        return self.projects.create(payload)

    def delete_project(self, project_id: UUID) -> bool:
        return self.projects.delete(project_id)

    def get_project_detail(self, project_id: UUID) -> ProjectDetail | None:
        project = self.projects.get(project_id)
        if not project:
            return None
        stats = self.projects.get_stats(project_id)
        return ProjectDetail.model_validate({**project.__dict__, "stats": stats.model_dump()})

    def list_posts(self, project_id: UUID):
        return self.posts.list_by_project(project_id)

    def list_comments(self, project_id: UUID):
        return self.comments.list_by_project(project_id)
