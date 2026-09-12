from unittest.mock import AsyncMock, patch

import pytest
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.agent import ChatAgent

from .conftest import FakeToolCallingModel, fake_player, fake_repo


def _agent(responses, repo=None):
    return ChatAgent(
        model=FakeToolCallingModel(responses=responses),
        repo=repo or fake_repo(),
        checkpointer=InMemorySaver(),
    )


@pytest.mark.asyncio
async def test_web_fallback_runs_when_no_tool_was_used():
    agent = _agent([AIMessage(content="I do not have that in my data.")])
    with patch("app.agent.agent.web_answer", AsyncMock(return_value="From the web.")) as web:
        res = await agent.answer("who won the ballon d'or in 2025?", session_id="w1")
    web.assert_awaited_once()
    assert res.answer == "From the web."


@pytest.mark.asyncio
async def test_web_fallback_is_skipped_when_a_tool_answered():
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}],
        ),
        AIMessage(content="Player A leads."),
    ]
    agent = _agent(scripted, fake_repo(rows=[fake_player()]))
    with patch("app.agent.agent.web_answer", AsyncMock(return_value="unused")) as web:
        res = await agent.answer("top scorer?", session_id="w2")
    web.assert_not_awaited()
    assert res.answer == "Player A leads."


@pytest.mark.asyncio
async def test_allow_web_false_never_reaches_the_web():
    agent = _agent([AIMessage(content="not in my data")])
    with patch("app.agent.agent.web_answer", AsyncMock(return_value="unused")) as web:
        res = await agent.answer("q", session_id="w3", allow_web=False)
    web.assert_not_awaited()
    assert res.answer == "not in my data"


@pytest.mark.asyncio
async def test_graph_answer_is_kept_when_grounding_is_unavailable():
    agent = _agent([AIMessage(content="not in my data")])
    with patch("app.agent.agent.web_answer", AsyncMock(return_value=None)):
        res = await agent.answer("q", session_id="w4")
    assert res.answer == "not in my data"


@pytest.mark.asyncio
async def test_a_web_answer_is_marked_degraded_so_it_is_not_mistaken_for_app_data():
    agent = _agent([AIMessage(content="nothing here")])
    with patch("app.agent.agent.web_answer", AsyncMock(return_value="From the web.")):
        res = await agent.answer("q", session_id="w5")
    assert res.used_tools is False
    assert res.degraded is True


@pytest.mark.asyncio
async def test_web_answer_labels_its_source():
    # The label is prepended by the module, never left to the model (spec 8).
    from app.agent.web_fallback import WEB_LABEL, web_answer

    class _Res:
        content = "Rodri won it in 2024."

    class _Model:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, q):
            return _Res()

    with patch("app.agent.llm.build_chat_model", return_value=_Model()):
        out = await web_answer("who won the ballon d'or?")
    assert out.startswith(WEB_LABEL)
    assert "Rodri" in out


@pytest.mark.asyncio
async def test_web_answer_returns_none_when_the_call_fails():
    from app.agent.web_fallback import web_answer

    with patch("app.agent.llm.build_chat_model", side_effect=RuntimeError("no network")):
        assert await web_answer("anything") is None


@pytest.mark.asyncio
async def test_web_answer_returns_none_on_an_empty_reply():
    # An empty grounded answer must not become a bare label with nothing after it.
    from app.agent.web_fallback import web_answer

    class _Res:
        content = "   "

    class _Model:
        def bind_tools(self, tools):
            return self

        async def ainvoke(self, q):
            return _Res()

    with patch("app.agent.llm.build_chat_model", return_value=_Model()):
        assert await web_answer("anything") is None


def test_the_grounding_tool_shape_is_accepted_by_the_installed_library():
    # If an upgrade changes this shape, every fallback would fail at runtime only.
    from langchain_google_genai._function_utils import convert_to_genai_function_declarations

    from app.agent.web_fallback import _GROUNDING_TOOL

    converted = convert_to_genai_function_declarations([_GROUNDING_TOOL])
    assert converted[0].google_search is not None
