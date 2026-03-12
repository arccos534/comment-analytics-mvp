from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_v1_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/comment_analytics"
    redis_url: str = "redis://localhost:6379/0"

    demo_mode: bool = False
    background_jobs_enabled: bool = False
    ingestion_batch_size: int = 25
    default_lookback_days: int = 90
    sentence_transformer_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    provider_http_timeout_seconds: int = 30

    telegram_api_id: int | None = None
    telegram_api_hash: str | None = None
    telegram_session_string: str | None = None

    vk_api_token: str | None = None
    vk_api_version: str = "5.199"

    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    openai_compatible_model: str = "gpt-4o-mini"
    llm_summary_enabled: bool = False

    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
