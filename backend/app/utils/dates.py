from datetime import UTC, datetime, timedelta

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def default_since() -> datetime:
    settings = get_settings()
    return utcnow() - timedelta(days=settings.default_lookback_days)
