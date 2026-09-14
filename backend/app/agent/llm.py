"""Gemini chat model construction. The only place a provider is named.

Swapping provider (a future local Ollama, say) means changing this module only: everything
downstream depends on BaseChatModel and bind_tools, not on Gemini.
"""

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings


def build_chat_model(model: str | None = None) -> BaseChatModel:
    """Build the chat model. max_retries covers 429s with the SDK's own backoff."""
    # No temperature: Gemini 3.x uses fixed sampling and ignores it.
    return ChatGoogleGenerativeAI(
        model=model or settings.gemini_model,
        google_api_key=settings.gemini_api_key or None,
        max_retries=3,
    )


def build_fallback_model() -> BaseChatModel:
    """Build the model used when the primary fails (retired, overloaded or out of quota)."""
    return build_chat_model(settings.gemini_fallback_model)
