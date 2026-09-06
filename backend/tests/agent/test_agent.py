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
async def test_plain_answer_is_returned_without_tools():
    res = await _agent([AIMessage(content="Ronaldo plays as a forward.")]).answer(
        "what position does ronaldo play?", session_id="s1"
    )
    assert res.answer == "Ronaldo plays as a forward."
    assert res.used_tools is False
    assert res.degraded is False


@pytest.mark.asyncio
async def test_tool_call_is_dispatched_then_answered():
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "call-1"}],
        ),
        AIMessage(content="Player A leads with 10 goals."),
    ]
    repo = fake_repo(rows=[fake_player()])
    res = await _agent(scripted, repo).answer("top scorer?", session_id="s2")
    assert res.answer == "Player A leads with 10 goals."
    assert res.used_tools is True
    repo.get_players.assert_called_once()


@pytest.mark.asyncio
async def test_history_is_kept_per_session():
    agent = _agent([AIMessage(content="ok")])
    await agent.answer("first question", session_id="s3")
    turns = agent.history("s3")
    assert [t["role"] for t in turns] == ["user", "assistant"]
    assert turns[0]["content"] == "first question"


@pytest.mark.asyncio
async def test_sessions_do_not_leak_into_each_other():
    agent = _agent([AIMessage(content="ok")])
    await agent.answer("question in one", session_id="s4")
    assert agent.history("s5") == []


@pytest.mark.asyncio
async def test_history_never_exposes_tool_messages_or_arguments():
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}],
        ),
        AIMessage(content="Player A leads."),
    ]
    agent = _agent(scripted, fake_repo(rows=[fake_player()]))
    await agent.answer("top scorer?", session_id="s7")
    turns = agent.history("s7")
    assert [t["role"] for t in turns] == ["user", "assistant"]
    assert not any("attacking" in t["content"] for t in turns)


@pytest.mark.asyncio
async def test_model_failure_returns_the_generic_message():
    from app.agent.constants import GENERIC_ERROR

    model = FakeToolCallingModel(responses=[])  # index error on first call
    agent = ChatAgent(model=model, repo=fake_repo(), checkpointer=InMemorySaver())
    res = await agent.answer("anything", session_id="s6")
    assert res.answer == GENERIC_ERROR
    assert res.degraded is True


@pytest.mark.asyncio
async def test_clear_drops_the_thread():
    agent = _agent([AIMessage(content="ok")])
    await agent.answer("remember this", session_id="s8")
    assert agent.history("s8")
    agent.clear("s8")
    assert agent.history("s8") == []
