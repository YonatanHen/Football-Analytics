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
    assert res.degraded is True  # no tool backed it, so it is not from the app's data


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


@pytest.mark.asyncio
async def test_a_tool_from_an_earlier_turn_does_not_count_for_this_turn():
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
    res = await agent.answer("who won the 2018 world cup?", session_id="x1")
    assert res.used_tools is False
    assert res.answer == "France won it."


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


@pytest.mark.asyncio
async def test_an_answer_with_no_tool_behind_it_is_marked_unverified():
    # The prompt lets the model answer outside questions from its own knowledge.
    res = await _agent([AIMessage(content="Not from the app's data: France won in 2018.")]).answer(
        "who won the 2018 world cup?", session_id="u1"
    )
    assert res.used_tools is False
    assert res.degraded is True


@pytest.mark.asyncio
async def test_history_hides_text_that_came_with_a_tool_call():
    # Such text is the model's preamble; the live view never showed it.
    scripted = [
        AIMessage(
            content="Let me check the attacking tool.",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}],
        ),
        AIMessage(content="Player A leads."),
    ]
    agent = _agent(scripted, fake_repo(rows=[fake_player()]))
    await agent.answer("top scorer?", session_id="h1")
    assert [t["content"] for t in agent.history("h1")] == ["top scorer?", "Player A leads."]


def test_clearing_a_session_survives_a_storage_failure():
    checkpointer = InMemorySaver()
    checkpointer.delete_thread = lambda session_id: (_ for _ in ()).throw(RuntimeError("mongo"))
    agent = ChatAgent(
        model=FakeToolCallingModel(responses=[]), repo=fake_repo(), checkpointer=checkpointer
    )
    agent.clear("gone")  # must not raise: the API returns 204 either way


@pytest.mark.asyncio
async def test_answer_reports_tool_names_and_row_counts_only():
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "t1"}],
        ),
        AIMessage(content="Player A leads with 10 goals."),
    ]
    res = await _agent(scripted, fake_repo(rows=[fake_player()])).answer("top?", session_id="t1")
    assert [(c.name, c.rows) for c in res.tool_calls] == [("attacking", 1)]
    assert res.uncited == []


@pytest.mark.asyncio
async def test_answer_lists_uncited_figures():
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "t2"}],
        ),
        AIMessage(content="Player A scored 41 goals."),
    ]
    res = await _agent(scripted, fake_repo(rows=[fake_player(goals=10)])).answer(
        "top?", session_id="t2"
    )
    assert res.degraded is True
    assert res.uncited == ["41"]
