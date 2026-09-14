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
async def test_list_of_content_parts_is_returned_as_plain_text():
    # Gemini 3.x returns content as parts, not a string.
    parts = [{"type": "text", "text": "Ronaldo plays "}, {"type": "text", "text": "as a forward."}]
    agent = _agent([AIMessage(content=parts)])
    res = await agent.answer("position?", session_id="p1")
    assert res.answer == "Ronaldo plays as a forward."
    assert agent.history("p1")[1]["content"] == "Ronaldo plays as a forward."


@pytest.mark.asyncio
async def test_citation_check_reads_content_parts():
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}],
        ),
        AIMessage(content=[{"type": "text", "text": "Player A scored 41 goals."}]),
    ]
    res = await _agent(scripted, fake_repo(rows=[fake_player(goals=10)])).answer(
        "top scorer?", session_id="p2"
    )
    assert res.answer == "Player A scored 41 goals."
    assert res.degraded is True


@pytest.mark.asyncio
async def test_fallback_model_answers_when_the_primary_fails():
    agent = ChatAgent(
        model=FakeToolCallingModel(responses=[]),  # raises on first call
        repo=fake_repo(),
        checkpointer=InMemorySaver(),
        fallback_models=[FakeToolCallingModel(responses=[AIMessage(content="from fallback")])],
    )
    res = await agent.answer("anything", session_id="f1")
    assert res.answer == "from fallback"
    assert res.degraded is False


@pytest.mark.asyncio
async def test_a_turn_is_saved_once_not_after_every_step():
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}],
        ),
        AIMessage(content="Player A leads."),
    ]
    saver = InMemorySaver()
    agent = ChatAgent(
        model=FakeToolCallingModel(responses=scripted),
        repo=fake_repo(rows=[fake_player()]),
        checkpointer=saver,
    )
    await agent.answer("top scorer?", session_id="d1")
    assert len(list(saver.list({"configurable": {"thread_id": "d1"}}))) == 1


@pytest.mark.asyncio
async def test_prune_runs_once_after_a_successful_turn():
    pruned = []
    agent = ChatAgent(
        model=FakeToolCallingModel(responses=[AIMessage(content="ok")]),
        repo=fake_repo(),
        checkpointer=InMemorySaver(),
        prune=pruned.append,
    )
    await agent.answer("hi", session_id="pr1")
    assert pruned == ["pr1"]


@pytest.mark.asyncio
async def test_prune_is_skipped_when_the_turn_fails():
    pruned = []
    agent = ChatAgent(
        model=FakeToolCallingModel(responses=[]),
        repo=fake_repo(),
        checkpointer=InMemorySaver(),
        prune=pruned.append,
    )
    await agent.answer("hi", session_id="pr2")
    assert pruned == []


@pytest.mark.asyncio
async def test_a_prune_failure_does_not_lose_the_answer():
    def broken(session_id):
        raise RuntimeError("mongo down")

    agent = ChatAgent(
        model=FakeToolCallingModel(responses=[AIMessage(content="ok")]),
        repo=fake_repo(),
        checkpointer=InMemorySaver(),
        prune=broken,
    )
    res = await agent.answer("hi", session_id="pr3")
    assert res.answer == "ok"
    assert res.degraded is False


@pytest.mark.asyncio
async def test_a_tool_from_an_earlier_turn_does_not_count_for_this_turn():
    from unittest.mock import AsyncMock, patch

    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}],
        ),
        AIMessage(content="Player A leads."),
        AIMessage(content="France won it."),  # second turn: no tool
    ]
    agent = _agent(scripted, fake_repo(rows=[fake_player()]))
    await agent.answer("top scorer?", session_id="x1")
    with patch("app.agent.agent.web_answer", AsyncMock(return_value="From the web.")) as web:
        res = await agent.answer("who won the 2018 world cup?", session_id="x1")
    web.assert_awaited_once()
    assert res.used_tools is False


@pytest.mark.asyncio
async def test_rows_from_an_earlier_turn_do_not_support_this_answer():
    call = {"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}
    scripted = [
        AIMessage(content="", tool_calls=[call]),
        AIMessage(content="Player A has 41 goals."),
        AIMessage(content="", tool_calls=[{**call, "id": "c2"}]),
        AIMessage(content="Player A has 41 goals."),
    ]
    repo = fake_repo(rows=[fake_player(goals=41)])
    agent = _agent(scripted, repo)
    first = await agent.answer("top scorer?", session_id="x2")
    assert first.degraded is False
    repo.get_players.return_value = ([fake_player(goals=10)], 1)
    second = await agent.answer("and now?", session_id="x2")
    assert second.degraded is True  # 41 is only in the first turn's rows


@pytest.mark.asyncio
async def test_clear_drops_the_thread():
    agent = _agent([AIMessage(content="ok")])
    await agent.answer("remember this", session_id="s8")
    assert agent.history("s8")
    agent.clear("s8")
    assert agent.history("s8") == []
