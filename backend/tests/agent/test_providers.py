from unittest.mock import MagicMock, patch

import pytest

from app.agent.llm import build_chat_model, build_fallback_model
from app.agent.providers import PROVIDERS, get_provider
from app.config import settings


def test_gemini_is_the_default_provider_and_needs_no_configuration():
    assert settings.llm_provider == "gemini"
    # 3.6-flash is capped at 20 free requests a day, which the chat exhausts in minutes.
    assert get_provider(settings.llm_provider).default_model == "gemini-3.5-flash"


def test_every_provider_is_registered_under_its_own_name():
    assert {"gemini", "openai", "anthropic"} <= set(PROVIDERS)
    assert all(name == provider.name for name, provider in PROVIDERS.items())


def test_an_unknown_provider_names_the_valid_ones():
    with pytest.raises(ValueError, match="gemini"):
        get_provider("llama-at-home")


def test_the_configured_model_wins_over_the_provider_default():
    with patch.object(settings, "llm_model", "gemini-3.5-flash-lite"):
        with patch("app.agent.providers.ChatGoogleGenerativeAI") as ctor:
            build_chat_model()
    assert ctor.call_args.kwargs["model"] == "gemini-3.5-flash-lite"


def test_an_explicit_model_argument_wins_over_the_configuration():
    with patch("app.agent.providers.ChatGoogleGenerativeAI") as ctor:
        build_chat_model("some-other-model")
    assert ctor.call_args.kwargs["model"] == "some-other-model"


def test_a_paid_provider_without_a_model_says_which_setting_is_missing():
    with patch.object(settings, "llm_provider", "openai"), patch.object(settings, "llm_model", ""):
        with pytest.raises(ValueError, match="LLM_MODEL"):
            build_chat_model()


def test_a_paid_provider_builds_its_own_chat_class():
    module = MagicMock()
    with (
        patch.object(settings, "llm_provider", "anthropic"),
        patch.object(settings, "llm_model", "some-anthropic-model"),
        patch.object(settings, "llm_api_key", "k-1"),
    ):
        with patch("importlib.import_module", return_value=module):
            model = build_chat_model()
    assert model is module.ChatAnthropic.return_value
    assert module.ChatAnthropic.call_args.kwargs["model"] == "some-anthropic-model"


def test_a_missing_provider_package_explains_what_to_install():
    with (
        patch.object(settings, "llm_provider", "openai"),
        patch.object(settings, "llm_model", "some-openai-model"),
    ):
        with patch("importlib.import_module", side_effect=ImportError("no module")):
            with pytest.raises(RuntimeError, match="langchain-openai"):
                build_chat_model()


def test_the_generic_key_is_used_when_set():
    with patch.object(settings, "llm_api_key", "generic-key"):
        with patch("app.agent.providers.ChatGoogleGenerativeAI") as ctor:
            build_chat_model()
    assert ctor.call_args.kwargs["api_key"] == "generic-key"


def test_gemini_still_reads_the_key_this_project_already_ships():
    with (
        patch.object(settings, "llm_api_key", ""),
        patch.object(settings, "gemini_api_key", "legacy-key"),
    ):
        with patch("app.agent.providers.ChatGoogleGenerativeAI") as ctor:
            build_chat_model()
    assert ctor.call_args.kwargs["api_key"] == "legacy-key"


def test_an_unset_key_is_passed_as_none_so_the_sdk_reads_its_own_env_var():
    with patch.object(settings, "llm_api_key", ""), patch.object(settings, "gemini_api_key", ""):
        with patch("app.agent.providers.ChatGoogleGenerativeAI") as ctor:
            build_chat_model()
    assert ctor.call_args.kwargs["api_key"] is None


def test_a_gemini_key_is_never_sent_to_another_provider():
    module = MagicMock()
    with (
        patch.object(settings, "llm_provider", "openai"),
        patch.object(settings, "llm_model", "m"),
        patch.object(settings, "llm_api_key", ""),
        patch.object(settings, "gemini_api_key", "gemini-only"),
    ):
        with patch("importlib.import_module", return_value=module):
            build_chat_model()
    assert module.ChatOpenAI.call_args.kwargs["api_key"] is None


def test_there_is_no_fallback_model_unless_one_is_configured():
    assert settings.llm_fallback_model == ""
    assert build_fallback_model() is None


def test_a_configured_fallback_model_is_built_with_the_same_provider():
    with patch.object(settings, "llm_fallback_model", "gemini-3.5-flash-lite"):
        with patch("app.agent.providers.ChatGoogleGenerativeAI") as ctor:
            model = build_fallback_model()
    assert model is ctor.return_value
    assert ctor.call_args.kwargs["model"] == "gemini-3.5-flash-lite"


def test_no_network_call_is_made_when_building_the_model():
    # The agent is built at startup; a call here would stop the app from booting.
    with patch("app.agent.providers.ChatGoogleGenerativeAI") as ctor:
        model = build_chat_model()
    assert model is ctor.return_value
    ctor.return_value.invoke.assert_not_called()


def test_the_installed_gemini_class_accepts_every_kwarg_we_pass():
    from langchain_core.language_models import BaseChatModel
    from langchain_google_genai import ChatGoogleGenerativeAI

    fields = ChatGoogleGenerativeAI.model_fields
    accepted = set(fields) | {f.alias for f in fields.values() if f.alias}
    assert {"model", "api_key", "max_retries"} <= accepted  # api_key is an alias
    assert issubclass(ChatGoogleGenerativeAI, BaseChatModel)
    assert ChatGoogleGenerativeAI(model="m", api_key="k").google_api_key is not None
