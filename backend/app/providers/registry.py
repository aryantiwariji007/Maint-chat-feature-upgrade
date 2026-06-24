from app.config import settings
from app.providers.anthropic_provider import AnthropicProvider
from app.providers.base import LLMProvider
from app.providers.gemini_provider import GeminiProvider


class ProviderNotConfiguredError(Exception):
    pass


_providers: dict[str, LLMProvider] = {}


def _build_providers() -> dict[str, LLMProvider]:
    providers: dict[str, LLMProvider] = {}
    if settings.gemini_api_key:
        providers["gemini"] = GeminiProvider(settings.gemini_api_key, settings.gemini_model)
    if settings.anthropic_api_key:
        providers["anthropic"] = AnthropicProvider(
            settings.anthropic_api_key, settings.anthropic_model
        )
    return providers


def get_provider(name: str) -> LLMProvider:
    if not _providers:
        _providers.update(_build_providers())
    provider = _providers.get(name)
    if provider is None:
        raise ProviderNotConfiguredError(
            f"Provider '{name}' is not configured (missing API key) or is not a known provider."
        )
    return provider
