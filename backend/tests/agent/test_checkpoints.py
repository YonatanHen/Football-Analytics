import mongomock
import pytest
from langchain_core.messages import AIMessage

from app.agent.agent import ChatAgent
from app.agent.checkpoints import build_checkpointer, keep_latest_checkpoint
from app.config import settings

from .conftest import FakeToolCallingModel, fake_player, fake_repo

WEEK = 7 * 24 * 60 * 60


def _tool_turn_then_plain_turn():
    return [
        AIMessage(
            content="",
            tool_calls=[{"name": "attacking", "args": {"metric": "goals"}, "id": "c1"}],
        ),
        AIMessage(content="Player A leads with 10 goals."),
        AIMessage(content="You asked about top scorers."),
    ]


@pytest.fixture
def mongo():
    return mongomock.MongoClient()


@pytest.fixture
def saver(mongo):
    return build_checkpointer(mongo)


def _agent(saver, responses):
    return ChatAgent(
        model=FakeToolCallingModel(responses=responses),
        repo=fake_repo(rows=[fake_player()]),
        checkpointer=saver,
        prune=lambda session_id: keep_latest_checkpoint(saver, session_id),
    )


def test_session_ttl_defaults_to_one_week():
    assert settings.chat_session_ttl_seconds == WEEK


def test_checkpoints_expire_after_the_configured_ttl(saver):
    indexes = saver.checkpoint_collection.index_information().values()
    assert any(ix.get("expireAfterSeconds") == WEEK for ix in indexes)


@pytest.mark.asyncio
async def test_a_session_is_stored_as_one_document(saver):
    agent = _agent(saver, _tool_turn_then_plain_turn())
    await agent.answer("top scorer?", session_id="t1")
    await agent.answer("what did I ask?", session_id="t1")
    assert saver.checkpoint_collection.count_documents({"thread_id": "t1"}) == 1
    assert saver.writes_collection.count_documents({"thread_id": "t1"}) == 0


@pytest.mark.asyncio
async def test_history_survives_pruning(saver):
    # Guard: if an upgrade stores deltas instead of full state, pruning would empty history.
    agent = _agent(saver, _tool_turn_then_plain_turn())
    await agent.answer("top scorer?", session_id="t2")
    await agent.answer("what did I ask?", session_id="t2")
    assert agent.history("t2") == [
        {"role": "user", "content": "top scorer?"},
        {"role": "assistant", "content": "Player A leads with 10 goals."},
        {"role": "user", "content": "what did I ask?"},
        {"role": "assistant", "content": "You asked about top scorers."},
    ]


@pytest.mark.asyncio
async def test_the_kept_document_carries_the_ttl_timestamp(saver):
    agent = _agent(saver, [AIMessage(content="ok")])
    await agent.answer("hi", session_id="t3")
    assert saver.checkpoint_collection.find_one({"thread_id": "t3"})["created_at"]


@pytest.mark.asyncio
async def test_pruning_one_session_leaves_other_sessions_alone(saver):
    agent = _agent(saver, [AIMessage(content="ok")])
    await agent.answer("one", session_id="a")
    await agent.answer("two", session_id="b")
    keep_latest_checkpoint(saver, "a")
    assert agent.history("b") == [
        {"role": "user", "content": "two"},
        {"role": "assistant", "content": "ok"},
    ]


def test_pruning_an_unknown_session_is_a_no_op(saver):
    keep_latest_checkpoint(saver, "never-used")
    assert saver.checkpoint_collection.count_documents({}) == 0
