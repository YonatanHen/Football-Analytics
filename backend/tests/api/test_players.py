import mongomock
import pytest
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app, get_repo
from app.infrastructure.mongo_repository import MongoRepository
from app.domain.models import PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores


@asynccontextmanager
async def _noop_lifespan(app):  # type: ignore[type-arg]
    yield


def _make_player(player_id: str = "1", season: str = "2025-2026") -> PlayerDTO:
    stats = Stats(goals=5, assists=3, xg=4.0, xa=2.5, minutes=900)
    score = Score(offensive=35.5, defensive=0.0, tactical=1.0, s_final=4.06)
    return PlayerDTO(
        sofascore_player_id=player_id, name="Test Player", season=season,
        position="FW", position_exact="ST", team="Arsenal",
        nationality="England", photo_url="https://example.com/p.jpg",
        competitions=[CompetitionEntry("England Premier League", stats, score)],
        aggregated_stats=stats,
        aggregated_scores=AggregatedScores(
            offensive=35.5, defensive=0.0, tactical=1.0, s_final=4.06,
            underpredicted_ratio=1.3, underpredicted_flag="HIGH_VALUE",
        ),
        low_sample_size=False,
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


@pytest.fixture
def client() -> TestClient:
    mc = mongomock.MongoClient()
    repo = MongoRepository(mc)
    app.dependency_overrides[get_repo] = lambda: repo
    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_player() -> TestClient:
    mc = mongomock.MongoClient()
    repo = MongoRepository(mc)
    repo.upsert_player(_make_player("1", "2025-2026"))
    app.dependency_overrides[get_repo] = lambda: repo
    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_players_empty(client: TestClient) -> None:
    resp = client.get("/v1/players")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 0
    assert body["data"] == []


def test_list_players_returns_player(client_with_player: TestClient) -> None:
    resp = client_with_player.get("/v1/players")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_list_players_filter_position(client_with_player: TestClient) -> None:
    resp = client_with_player.get("/v1/players?position=GK")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_get_player_found(client_with_player: TestClient) -> None:
    resp = client_with_player.get("/v1/players/1")
    assert resp.status_code == 200
    assert resp.json()["sofascore_player_id"] == "1"
    assert resp.json()["aggregated_scores"]["underpredicted_flag"] == "HIGH_VALUE"


def test_get_player_not_found(client: TestClient) -> None:
    resp = client.get("/v1/players/nonexistent")
    assert resp.status_code == 404


def test_scatter_data_empty(client: TestClient) -> None:
    resp = client.get("/v1/analysis/scatter")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_scatter_data_with_player(client_with_player: TestClient) -> None:
    resp = client_with_player.get("/v1/analysis/scatter")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["xg_xa"] == pytest.approx(6.5)
    assert data[0]["g_a"] == pytest.approx(8.0)


def test_list_players_filter_by_name_partial(client_with_player: TestClient) -> None:
    resp = client_with_player.get("/v1/players?name=Test")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_list_players_filter_by_name_case_insensitive(client_with_player: TestClient) -> None:
    resp = client_with_player.get("/v1/players?name=test+player")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_list_players_filter_by_name_no_match(client_with_player: TestClient) -> None:
    resp = client_with_player.get("/v1/players?name=Nonexistent")
    assert resp.status_code == 200
    assert resp.json()["total"] == 0
