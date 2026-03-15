import hashlib
import re
from urllib.parse import urlsplit, urlunsplit


def normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_url(url: str) -> str:
    cleaned = normalize_whitespace(url).strip()
    if not cleaned:
        return ""

    if not re.match(r"^[a-z]+://", cleaned, re.IGNORECASE):
        cleaned = f"https://{cleaned}"

    parts = urlsplit(cleaned)
    scheme = (parts.scheme or "https").lower()
    host = (parts.netloc or "").lower()
    path = re.sub(r"/{2,}", "/", parts.path or "").rstrip("/")
    if host in {"telegram.me", "www.telegram.me"}:
        host = "t.me"
    if host in {"www.t.me"}:
        host = "t.me"
    if host in {"m.vk.com", "www.vk.com"}:
        host = "vk.com"

    if host == "t.me" and path.startswith("/s/"):
        path = path[2:]

    normalized = urlunsplit((scheme, host, path, "", ""))
    return normalized.rstrip("/")


def hash_external_author_id(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
