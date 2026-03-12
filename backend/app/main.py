from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.analytics import router as analytics_router
from app.api.routes.comments import router as comments_router
from app.api.routes.health import router as health_router
from app.api.routes.ingestion import router as ingestion_router
from app.api.routes.posts import router as posts_router
from app.api.routes.projects import router as projects_router
from app.api.routes.sources import router as sources_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.base import Base
from app.db.session import engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()

    app = FastAPI(title="Comment Analytics MVP", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(projects_router, prefix=settings.api_v1_prefix)
    app.include_router(sources_router, prefix=settings.api_v1_prefix)
    app.include_router(ingestion_router, prefix=settings.api_v1_prefix)
    app.include_router(posts_router, prefix=settings.api_v1_prefix)
    app.include_router(comments_router, prefix=settings.api_v1_prefix)
    app.include_router(analytics_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
