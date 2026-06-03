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
            underpredicted_ratio=1.3, underpredicted_flag="HIGH_VALUE",
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
    assert result.aggregated_scores.underpredicted_flag == "HIGH_VALUE"


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


def test_get_players_filter_by_underpredicted_flag(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1"))
    players, total = repo.get_players(season="2025-2026", underpredicted_flag="HIGH_VALUE")
    assert total == 1
    _, total_miss = repo.get_players(season="2025-2026", underpredicted_flag="OVERPERFORMING")
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


def test_get_players_filter_by_name_exact(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1"))
    players, total = repo.get_players(season="2025-2026", name="Test Player")
    assert total == 1
    assert players[0].name == "Test Player"


def test_get_players_filter_by_name_partial(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1"))
    players, total = repo.get_players(season="2025-2026", name="Test")
    assert total == 1


def test_get_players_filter_by_name_case_insensitive(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1"))
    _, total = repo.get_players(season="2025-2026", name="test player")
    assert total == 1


def test_get_players_filter_by_name_no_match(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1"))
    _, total = repo.get_players(season="2025-2026", name="Nonexistent")
    assert total == 0


def test_get_players_filter_by_name_matches_substring(repo: MongoRepository) -> None:
    p1 = _make_player("1")
    p1.name = "Mohamed Salah"
    p2 = _make_player("2")
    p2.name = "Salah Mejri"
    repo.upsert_player(p1)
    repo.upsert_player(p2)
    _, total = repo.get_players(season="2025-2026", name="Salah")
    assert total == 2


def test_sofascore_upsert_overwrites_legacy_kaggle_doc_without_norm_fields(repo: MongoRepository) -> None:
    """Sofascore upsert must merge with legacy Kaggle docs that lack norm_name/norm_team."""
    # Insert a Kaggle-origin doc the old way: no norm_name or norm_team
    repo._players.insert_one({
        "sofascore_player_id": None,
        "name": "Kenan Yıldız",
        "team": "Juventus",
        "season": "2025-2026",
        # deliberately omit norm_name / norm_team
    })
    assert repo._players.count_documents({"name": "Kenan Yıldız"}) == 1

    # Upsert the Sofascore version
    p = _make_player("1149011")
    p.name = "Kenan Yıldız"
    p.team = "Juventus"
    repo.upsert_player(p)

    # Must still be exactly one document (no duplicate)
    count = repo._players.count_documents({"name": "Kenan Yıldız", "season": "2025-2026"})
    assert count == 1
    doc = repo._players.find_one({"sofascore_player_id": "1149011"})
    assert doc is not None
