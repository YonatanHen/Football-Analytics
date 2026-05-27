import pytest
from datetime import datetime, timezone
from app.domain.models import (
    PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores,
)
from app.infrastructure.mongo_repository import MongoRepository


def _make_player(player_id: str = "123", season: str = "2025-2026") -> PlayerDTO:
    stats = Stats(goals=5, assists=3, xg=4.0, xa=2.5, minutes=900)
    score = Score(offensive=35.5, defensive=0.0, tactical=1.0, s_final=4.06)
    return PlayerDTO(
        sofascore_player_id=player_id,
        name="Test Player",
        season=season,
        position="FW",
        position_exact="ST",
        team="Arsenal",
        nationality="England",
        photo_url="https://example.com/photo.jpg",
        competitions=[CompetitionEntry("England Premier League", stats, score)],
        aggregated_stats=stats,
        aggregated_scores=AggregatedScores(
            offensive=35.5, defensive=0.0, tactical=1.0, s_final=4.06,
            sleeper_ratio=1.3, sleeper_flag="HIGH_VALUE",
        ),
        low_sample_size=False,
        last_updated=datetime.now(timezone.utc).isoformat(),
    )


def test_upsert_and_get_player(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("123", "2025-2026"))
    result = repo.get_player("123", "2025-2026")
    assert result is not None
    assert result.sofascore_player_id == "123"
    assert result.name == "Test Player"
    assert result.aggregated_stats.goals == 5
    assert result.aggregated_scores.sleeper_flag == "HIGH_VALUE"


def test_upsert_overwrites_existing(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("123"))
    updated = _make_player("123")
    updated.name = "Updated Name"
    repo.upsert_player(updated)
    result = repo.get_player("123", "2025-2026")
    assert result is not None
    assert result.name == "Updated Name"


def test_get_player_not_found_returns_none(repo: MongoRepository) -> None:
    assert repo.get_player("nonexistent", "2025-2026") is None


def test_get_players_filter_by_position(repo: MongoRepository) -> None:
    fw = _make_player("1")
    gk = _make_player("2")
    gk.position = "GK"
    repo.upsert_player(fw)
    repo.upsert_player(gk)
    players, total = repo.get_players(season="2025-2026", position="GK")
    assert total == 1
    assert players[0].sofascore_player_id == "2"


def test_get_players_filter_by_team(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1"))
    players, total = repo.get_players(season="2025-2026", team="Arsenal")
    assert total == 1
    _, total_miss = repo.get_players(season="2025-2026", team="Chelsea")
    assert total_miss == 0


def test_get_players_filter_by_sleeper_flag(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1"))
    players, total = repo.get_players(season="2025-2026", sleeper_flag="HIGH_VALUE")
    assert total == 1
    _, total_miss = repo.get_players(season="2025-2026", sleeper_flag="OVERPERFORMING")
    assert total_miss == 0


def test_get_players_pagination(repo: MongoRepository) -> None:
    for i in range(5):
        repo.upsert_player(_make_player(str(i)))
    players, total = repo.get_players(season="2025-2026", page=1, page_size=3)
    assert total == 5
    assert len(players) == 3


def test_get_players_separate_seasons(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1", "2025-2026"))
    repo.upsert_player(_make_player("1", "2024-2025"))
    _, t1 = repo.get_players(season="2025-2026")
    _, t2 = repo.get_players(season="2024-2025")
    assert t1 == 1
    assert t2 == 1


def test_log_scrape(repo: MongoRepository) -> None:
    entry = repo.log_scrape(
        season="2025-2026",
        competitions=["England Premier League"],
        players_upserted=42,
        status="success",
    )
    assert entry["players_upserted"] == 42
    assert entry["status"] == "success"
    assert "_id" in entry


def test_get_scatter_data(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1"))
    data = repo.get_scatter_data("2025-2026")
    assert len(data) == 1
    assert "name" in data[0]
