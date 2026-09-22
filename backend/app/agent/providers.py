"""Chat model providers (strategy pattern). Gemini's free tier is the default.

Adding a provider means adding one subclass and listing it in PROVIDERS. Everything
downstream depends on BaseChatModel, never on a provider.
"""

import importlib
from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel
from langchain_google_genai import ChatGoogleGenerativeAI

MAX_RETRIES = 3


class ModelProvider(ABC):
    name: str
    package: str
    default_model: str = ""  # empty means the user must set LLM_MODEL

    @abstractmethod
    def create(self, model: str, api_key: str | None) -> BaseChatModel:
        """Build the chat model. Must not make a network call."""

    def _class_from(self, module_name: str, class_name: str):
        try:
            return getattr(importlib.import_module(module_name), class_name)
        except ImportError as exc:
            raise RuntimeError(
                f"Provider {self.name!r} needs a package: pip install {self.package}"
            ) from exc


class GeminiProvider(ModelProvider):
    name = "gemini"
    package = "langchain-google-genai"
    default_model = "gemini-3.5-flash"  # free tier; 3.6-flash allows only 20 requests/day

    def create(self, model: str, api_key: str | None) -> BaseChatModel:
        # No temperature: Gemini 3.x uses fixed sampling and ignores it.
        return ChatGoogleGenerativeAI(model=model, api_key=api_key, max_retries=MAX_RETRIES)


class OpenAIProvider(ModelProvider):
    name = "openai"
    package = "langchain-openai"

    def create(self, model: str, api_key: str | None) -> BaseChatModel:
        chat_class = self._class_from("langchain_openai", "ChatOpenAI")
        return chat_class(model=model, api_key=api_key, max_retries=MAX_RETRIES)


class AnthropicProvider(ModelProvider):
    name = "anthropic"
    package = "langchain-anthropic"

    def create(self, model: str, api_key: str | None) -> BaseChatModel:
        chat_class = self._class_from("langchain_anthropic", "ChatAnthropic")
        return chat_class(model=model, api_key=api_key, max_retries=MAX_RETRIES)


PROVIDERS: dict[str, ModelProvider] = {
    p.name: p for p in (GeminiProvider(), OpenAIProvider(), AnthropicProvider())
}


def get_provider(name: str) -> ModelProvider:
    try:
        return PROVIDERS[name]
    except KeyError:
        raise ValueError(
            f"Unknown LLM_PROVIDER {name!r}. Available: {', '.join(sorted(PROVIDERS))}."
        ) from None
