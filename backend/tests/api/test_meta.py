import mongomock
from fastapi.testclient import TestClient

from app.config import settings
from app.infrastructure.mongo_repository import MongoRepository
from app.main import app, get_repo

from .test_players import _make_player, _noop_lifespan


def _client(repo: MongoRepository) -> TestClient:
    app.dependency_overrides[get_repo] = lambda: repo
    app.router.lifespan_context = _noop_lifespan
    return TestClient(app)


def test_meta_on_an_empty_database() -> None:
    with _client(MongoRepository(mongomock.MongoClient())) as c:
        body = c.get("/v1/meta").json()
    app.dependency_overrides.clear()
    assert body["players_total"] == 0
    assert body["last_updated"] is None
    assert body["seasons"] == []
    assert body["agent"]["max_tool_calls"] == settings.agent_max_tool_iterations
    assert body["agent"]["model"]


def test_meta_counts_players_and_lists_seasons() -> None:
    repo = MongoRepository(mongomock.MongoClient())
    repo.upsert_player(_make_player("1", "2025-2026"))
    repo.upsert_player(_make_player("2", "2025-2026"))
    repo.upsert_player(_make_player("1", "2024-2025"))
    repo.set_league_total_matches("England Premier League", "2025-2026", 10)
    with _client(repo) as c:
        body = c.get("/v1/meta?season=2025-2026").json()
    app.dependency_overrides.clear()
    assert body["players_total"] == 2
    assert body["seasons"] == ["2025-2026", "2024-2025"]
    assert body["last_updated"].startswith("20")
