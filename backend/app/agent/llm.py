"""Chat model construction. The provider and model come from configuration."""

from langchain_core.language_models import BaseChatModel

from app.agent.providers import ModelProvider, get_provider
from app.config import settings


def build_chat_model(model: str | None = None) -> BaseChatModel:
    provider = get_provider(settings.llm_provider)
    name = model or settings.llm_model or provider.default_model
    if not name:
        raise ValueError(f"Provider {provider.name!r} has no default model: set LLM_MODEL.")
    return provider.create(name, _api_key(provider))


def build_fallback_model() -> BaseChatModel | None:
    """The model used when the primary one fails. None unless LLM_FALLBACK_MODEL is set."""
    return build_chat_model(settings.llm_fallback_model) if settings.llm_fallback_model else None


def _api_key(provider: ModelProvider) -> str | None:
    if settings.llm_api_key:
        return settings.llm_api_key
    if provider.name == "gemini" and settings.gemini_api_key:
        return settings.gemini_api_key  # the key name this project already ships with
    return None  # let the provider SDK read its own environment variable
