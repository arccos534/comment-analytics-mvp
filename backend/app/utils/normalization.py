import hashlib
import re


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_url(url: str) -> str:
    cleaned = normalize_whitespace(url).strip().rstrip("/")
    return cleaned


def hash_external_author_id(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
