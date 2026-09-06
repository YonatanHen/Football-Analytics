from unittest.mock import patch

from app.agent.llm import FALLBACK_CHAIN, build_chat_model
from app.config import settings


def test_fallback_chain_is_primary_then_fallback():
    assert FALLBACK_CHAIN == [settings.gemini_model, settings.gemini_fallback_model]


def test_build_chat_model_uses_the_configured_model_and_key():
    with patch("app.agent.llm.ChatGoogleGenerativeAI") as ctor:
        build_chat_model()
    kwargs = ctor.call_args.kwargs
    assert kwargs["model"] == settings.gemini_model
    assert kwargs["max_retries"] >= 2


def test_build_chat_model_accepts_an_explicit_model():
    with patch("app.agent.llm.ChatGoogleGenerativeAI") as ctor:
        build_chat_model("some-other-model")
    assert ctor.call_args.kwargs["model"] == "some-other-model"


def test_temperature_is_zero_so_the_same_question_routes_the_same_way():
    with patch("app.agent.llm.ChatGoogleGenerativeAI") as ctor:
        build_chat_model()
    assert ctor.call_args.kwargs["temperature"] == 0


def test_an_unset_api_key_is_passed_as_none_not_empty_string():
    # "" would be sent as a real credential and fail with a confusing 400; None lets the
    # SDK fall back to its own environment lookup.
    with patch.object(settings, "gemini_api_key", ""):
        with patch("app.agent.llm.ChatGoogleGenerativeAI") as ctor:
            build_chat_model()
    assert ctor.call_args.kwargs["google_api_key"] is None


def test_configured_api_key_is_forwarded():
    with patch.object(settings, "gemini_api_key", "test-key-123"):
        with patch("app.agent.llm.ChatGoogleGenerativeAI") as ctor:
            build_chat_model()
    assert ctor.call_args.kwargs["google_api_key"] == "test-key-123"


def test_no_network_call_is_made_when_building_the_model():
    # Construction must stay lazy: the agent is built at app startup, and a network call
    # there would make the service fail to boot when Gemini is unreachable.
    with patch("app.agent.llm.ChatGoogleGenerativeAI") as ctor:
        model = build_chat_model()
    assert model is ctor.return_value
    ctor.return_value.invoke.assert_not_called()


def test_the_installed_gemini_class_accepts_every_kwarg_we_pass():
    # Every other test patches the constructor, so nothing else would notice if a
    # langchain-google-genai upgrade renamed or dropped one of these.
    from langchain_core.language_models import BaseChatModel
    from langchain_google_genai import ChatGoogleGenerativeAI

    accepted = set(ChatGoogleGenerativeAI.model_fields)
    assert {"model", "google_api_key", "temperature", "max_retries"} <= accepted
    assert issubclass(ChatGoogleGenerativeAI, BaseChatModel)
    assert callable(ChatGoogleGenerativeAI.bind_tools)
