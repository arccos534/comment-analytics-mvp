from app.core.config import get_settings
from app.models.enums import PlatformEnum
from app.providers.base import BaseProvider, ProviderContext
from app.providers.telegram_provider import TelegramProvider
from app.providers.vk_provider import VkProvider


def get_provider(platform: PlatformEnum) -> BaseProvider:
    settings = get_settings()
    context = ProviderContext(demo_mode=settings.demo_mode)
    providers: dict[PlatformEnum, BaseProvider] = {
        PlatformEnum.telegram: TelegramProvider(context=context),
        PlatformEnum.vk: VkProvider(context=context),
    }
    return providers[platform]
