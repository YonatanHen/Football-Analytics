import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.agent import ChatAgent
from app.agent.answer_check import uncited_numbers

from .conftest import FakeToolCallingModel, fake_player, fake_repo

ROWS = [{"name": "Player A", "goals": 12, "s_final": 7.25, "minutes": 1200}]


def test_grounded_answer_has_no_uncited_numbers():
    assert uncited_numbers("Player A scored 12 goals in 1200 minutes.", ROWS) == []


def test_invented_number_is_flagged():
    assert uncited_numbers("Player A scored 19 goals.", ROWS) == ["19"]


def test_rounded_citation_is_accepted():
    # 7.25 rendered as 7.3 or 7 is a formatting choice, not a fabrication.
    assert uncited_numbers("His score is 7.3.", ROWS) == []
    assert uncited_numbers("His score is 7.2.", ROWS) == []
    assert uncited_numbers("His score is about 7.", ROWS) == []


def test_a_number_close_to_a_row_value_but_outside_rounding_is_flagged():
    # 7.5 cannot be a rendering of 7.25; only genuine rounding is tolerated.
    assert uncited_numbers("His score is 7.5.", ROWS) == ["7.5"]


def test_ordinals_and_small_counts_are_ignored():
    # "top 5", "the 3 players" describe the query, not a stat.
    assert uncited_numbers("The top 5 are led by Player A.", ROWS) == []


def test_number_inside_a_name_is_not_a_statistic():
    rows = [{"name": "Player 750", "goals": 12}]
    assert uncited_numbers("Player 750 scored 12.", rows) == []


def test_every_invented_number_is_reported_not_just_the_first():
    out = uncited_numbers("He scored 19 goals and 23 assists.", ROWS)
    assert out == ["19", "23"]


def test_an_answer_with_no_rows_flags_every_real_figure():
    # The web fallback path has no rows; a figure there is ungrounded by definition.
    assert uncited_numbers("He scored 19 goals.", []) == ["19"]


def test_an_answer_with_no_numbers_is_clean():
    assert uncited_numbers("Player A leads the table.", ROWS) == []


def test_booleans_are_not_treated_as_citable_numbers():
    # low_sample_size=True must not make "1" a cited value.
    rows = [{"name": "Player A", "goals": 12, "low_sample_size": True}]
    assert uncited_numbers("He scored 41 goals.", rows) == ["41"]


@pytest.mark.asyncio
async def test_agent_flags_an_invented_figure_but_still_returns_the_answer():
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}],
        ),
        AIMessage(content="Player A scored 41 goals."),  # the row says 10
    ]
    agent = ChatAgent(
        model=FakeToolCallingModel(responses=scripted),
        repo=fake_repo(rows=[fake_player(goals=10)]),
        checkpointer=InMemorySaver(),
    )
    res = await agent.answer("top scorer?", session_id="ac1")
    assert res.answer == "Player A scored 41 goals."
    assert res.degraded is True


@pytest.mark.asyncio
async def test_agent_does_not_flag_a_grounded_answer():
    scripted = [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}],
        ),
        AIMessage(content="Player A scored 10 goals in 900 minutes."),
    ]
    agent = ChatAgent(
        model=FakeToolCallingModel(responses=scripted),
        repo=fake_repo(rows=[fake_player(goals=10)]),
        checkpointer=InMemorySaver(),
    )
    res = await agent.answer("top scorer?", session_id="ac2")
    assert res.degraded is False


def test_unreadable_tool_output_skips_the_check_rather_than_guessing():
    from app.agent.agent import _tool_rows

    assert _tool_rows([ToolMessage(content="not json", tool_call_id="c1")]) is None
