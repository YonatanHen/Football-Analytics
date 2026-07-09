from contextlib import asynccontextmanager
from unittest.mock import patch

import mongomock
import pytest
from fastapi.testclient import TestClient

from app.infrastructure.mongo_repository import MongoRepository
from app.main import app, get_repo


@asynccontextmanager
async def _noop_lifespan(app):  # type: ignore[type-arg]
    yield


@pytest.fixture
def client() -> TestClient:
    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_with_repo() -> TestClient:
    repo = MongoRepository(mongomock.MongoClient())
    app.dependency_overrides[get_repo] = lambda: repo
    app.router.lifespan_context = _noop_lifespan
    with TestClient(app) as c:
        yield c, repo
    app.dependency_overrides.clear()


def test_list_competitions_excludes_womens_leagues(client: TestClient) -> None:
    fake_comps_yaml = """
England Premier League:
  SOFASCORE: 17
England WSL:
  SOFASCORE: 1044
France Ligue 2:
  TRANSFERMARKT: https://example.com/ligue-2
"""
    with patch("app.api.fetch.resources.files") as mock_files:
        mock_files.return_value.joinpath.return_value.read_text.return_value = fake_comps_yaml
        resp = client.get("/v1/fetch/competitions")
    assert resp.status_code == 200
    assert resp.json() == ["England Premier League"]


def test_get_seasons_returns_season_map(client: TestClient) -> None:
    with patch(
        "app.api.fetch.SofascoreClient.get_valid_seasons",
        return_value={"25/26": 76986, "24/25": 61627},
    ):
        resp = client.get("/v1/fetch/seasons", params={"competition": "England Premier League"})
    assert resp.status_code == 200
    assert resp.json() == {"25/26": 76986, "24/25": 61627}


def test_get_seasons_unknown_competition_returns_404(client: TestClient) -> None:
    with patch(
        "app.api.fetch.SofascoreClient.get_valid_seasons",
        side_effect=ValueError("`league` must be a valid Sofascore league."),
    ):
        resp = client.get("/v1/fetch/seasons", params={"competition": "Not A League"})
    assert resp.status_code == 404


def test_get_fetched_leagues_empty(client_with_repo: tuple[TestClient, MongoRepository]) -> None:
    client, _repo = client_with_repo
    resp = client.get("/v1/fetch/fetched")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_fetched_leagues_returns_known_pairs(
    client_with_repo: tuple[TestClient, MongoRepository],
) -> None:
    client, repo = client_with_repo
    repo.set_league_total_matches("England Premier League", "2025-2026", 38)

    resp = client.get("/v1/fetch/fetched")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["competition"] == "England Premier League"
    assert body[0]["season"] == "2025-2026"
