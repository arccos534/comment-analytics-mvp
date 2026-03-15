import re

from app.models.enums import PlatformEnum, SourceTypeEnum
from app.providers.base import ProviderValidationResult
from app.utils.normalization import normalize_url

TELEGRAM_CHANNEL_RE = re.compile(r"^https?://t\.me/(?P<slug>[A-Za-z0-9_]+)/?$", re.IGNORECASE)
TELEGRAM_POST_RE = re.compile(r"^https?://t\.me/(?P<slug>[A-Za-z0-9_]+)/(?P<post_id>\d+)/?$", re.IGNORECASE)
VK_COMMUNITY_RE = re.compile(r"^https?://vk\.com/(?P<slug>[A-Za-z0-9_.-]+)/?$", re.IGNORECASE)
VK_POST_RE = re.compile(r"^https?://vk\.com/wall(?P<owner>-?\d+)_(?P<post_id>\d+)/?$", re.IGNORECASE)


def split_urls(raw_values: list[str]) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for raw in raw_values:
        for line in raw.splitlines():
            normalized = normalize_url(line)
            if normalized and normalized not in seen:
                urls.append(normalized)
                seen.add(normalized)
    return urls


def detect_platform_and_type(url: str) -> ProviderValidationResult:
    normalized = normalize_url(url)

    if not normalized:
        return ProviderValidationResult(
            url=url,
            normalized_url="",
            platform=None,
            source_type=None,
            is_valid=False,
            can_save=False,
            reason="Source URL is empty",
        )

    if match := TELEGRAM_POST_RE.match(normalized):
        slug = match.group("slug")
        post_id = match.group("post_id")
        return ProviderValidationResult(
            url=url,
            normalized_url=normalized,
            platform=PlatformEnum.telegram,
            source_type=SourceTypeEnum.post,
            is_valid=True,
            can_save=True,
            external_source_id=f"{slug}:{post_id}",
            title=f"Telegram post @{slug}",
        )

    if match := TELEGRAM_CHANNEL_RE.match(normalized):
        slug = match.group("slug")
        return ProviderValidationResult(
            url=url,
            normalized_url=normalized,
            platform=PlatformEnum.telegram,
            source_type=SourceTypeEnum.channel,
            is_valid=True,
            can_save=True,
            external_source_id=slug,
            title=f"Telegram channel @{slug}",
        )

    if match := VK_POST_RE.match(normalized):
        owner = match.group("owner")
        post_id = match.group("post_id")
        return ProviderValidationResult(
            url=url,
            normalized_url=normalized,
            platform=PlatformEnum.vk,
            source_type=SourceTypeEnum.post,
            is_valid=True,
            can_save=True,
            external_source_id=f"{owner}_{post_id}",
            title=f"VK post wall{owner}_{post_id}",
        )

    if match := VK_COMMUNITY_RE.match(normalized):
        slug = match.group("slug")
        return ProviderValidationResult(
            url=url,
            normalized_url=normalized,
            platform=PlatformEnum.vk,
            source_type=SourceTypeEnum.community,
            is_valid=True,
            can_save=True,
            external_source_id=slug,
            title=f"VK community {slug}",
        )

    return ProviderValidationResult(
        url=url,
        normalized_url=normalized,
        platform=None,
        source_type=None,
        is_valid=False,
        can_save=False,
        reason="Unsupported or invalid source URL",
    )
