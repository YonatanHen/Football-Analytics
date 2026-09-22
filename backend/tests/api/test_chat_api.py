from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app import dependencies, main
from app.agent.agent import ChatResult
from app.agent.constants import GENERIC_ERROR
from app.main import app


@asynccontextmanager
async def _noop_lifespan(app):  # type: ignore[type-arg]
    yield


@pytest.fixture
def agent():
    return MagicMock()


@pytest.fixture
def client(agent):
    app.dependency_overrides[dependencies.get_agent] = lambda: agent
    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_chat_returns_the_answer_only(client, agent):
    agent.answer = AsyncMock(return_value=ChatResult(answer="Player A leads.", used_tools=True))
    r = client.post("/v1/chat", json={"session_id": "s1", "message": "top scorer?"})
    assert r.status_code == 200
    assert r.json() == {"answer": "Player A leads.", "session_id": "s1", "degraded": False}
    agent.answer.assert_awaited_once_with("top scorer?", session_id="s1")


def test_chat_passes_the_degraded_flag_through(client, agent):
    agent.answer = AsyncMock(return_value=ChatResult(answer="x", used_tools=False, degraded=True))
    r = client.post("/v1/chat", json={"session_id": "s1", "message": "q"})
    assert r.json()["degraded"] is True


def test_chat_hides_internal_failures_behind_a_generic_message(client, agent):
    agent.answer = AsyncMock(side_effect=RuntimeError("mongo exploded at /srv/app/x.py"))
    r = client.post("/v1/chat", json={"session_id": "s2", "message": "hi"})
    assert r.status_code == 200
    assert r.json()["answer"] == GENERIC_ERROR
    assert r.json()["degraded"] is True
    assert "mongo" not in r.text.lower()


def test_chat_rejects_an_empty_message(client, agent):
    r = client.post("/v1/chat", json={"session_id": "s1", "message": ""})
    assert r.status_code == 422


def test_chat_rejects_an_oversized_message(client, agent):
    r = client.post("/v1/chat", json={"session_id": "s1", "message": "x" * 2001})
    assert r.status_code == 422


def test_chat_rejects_an_empty_session_id(client, agent):
    r = client.post("/v1/chat", json={"session_id": "", "message": "hi"})
    assert r.status_code == 422


def test_get_session_replays_turns(client, agent):
    turns = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    agent.history.return_value = turns
    r = client.get("/v1/chat/sessions/s3")
    assert r.status_code == 200
    assert r.json() == {"turns": turns}


def test_delete_session_clears_the_thread(client, agent):
    r = client.delete("/v1/chat/sessions/s4")
    assert r.status_code == 204
    agent.clear.assert_called_once_with("s4")


@pytest.fixture
def client_without_agent():
    app.dependency_overrides[dependencies.get_agent] = lambda: None
    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_chat_without_an_agent_returns_the_generic_message(client_without_agent):
    r = client_without_agent.post("/v1/chat", json={"session_id": "s1", "message": "hi"})
    assert r.status_code == 200
    assert r.json() == {"answer": GENERIC_ERROR, "session_id": "s1", "degraded": True}


def test_session_endpoints_without_an_agent_do_not_fail(client_without_agent):
    assert client_without_agent.get("/v1/chat/sessions/s1").json() == {"turns": []}
    assert client_without_agent.delete("/v1/chat/sessions/s1").status_code == 204


def test_startup_survives_an_agent_that_cannot_be_built():
    # A missing GEMINI_API_KEY raises at construction; the rest of the app must still start.
    original = app.router.lifespan_context
    app.router.lifespan_context = main.lifespan
    try:
        with (
            patch.object(main, "MongoClient", MagicMock()),
            patch.object(main, "MongoRepository", MagicMock()),
            patch.object(main, "ModeFactory", MagicMock()),
            patch.object(main, "build_agent", side_effect=ValueError("API key required")),
        ):
            with TestClient(app):
                assert dependencies._agent is None
                assert dependencies._repo is not None
    finally:
        app.router.lifespan_context = original
        dependencies._repo = dependencies._mode_factory = dependencies._agent = None
