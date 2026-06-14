import pytest
from datetime import datetime, timezone
from app.domain.models import (
    PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores,
)
from app.infrastructure.mongo_repository import MongoRepository
from app.infrastructure.text_utils import normalize_text


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


def test_upsert_and_get_player_bio_fields(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("123"))
    result = repo.get_player("123", "2025-2026")
    assert result is not None
    assert result.nationality == "England"
    assert result.position == "FW"
    assert result.position_exact == "ST"


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


def test_bio_shared_across_seasons(repo: MongoRepository) -> None:
    repo.upsert_player(_make_player("1", "2025-2026"))
    repo.upsert_player(_make_player("1", "2024-2025"))
    assert repo._player_bios.count_documents({"sofascore_player_id": "1"}) == 1
    assert repo._player_stats.count_documents({"season": "2025-2026"}) == 1
    assert repo._player_stats.count_documents({"season": "2024-2025"}) == 1


def test_upsert_player_bio_updates_nationality(repo: MongoRepository) -> None:
    p = _make_player("1")
    p.nationality = ""
    repo.upsert_player(p)
    repo.upsert_player_bio("1", nationality="Spain", position_exact="RW")
    result = repo.get_player("1", "2025-2026")
    assert result is not None
    assert result.nationality == "Spain"
    assert result.position_exact == "RW"


def test_log_fetch(repo: MongoRepository) -> None:
    entry = repo.log_fetch(
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


def test_sofascore_upsert_merges_with_kaggle_bio(repo: MongoRepository) -> None:
    """When a Sofascore upsert matches an existing Kaggle-origin bio, it merges (no duplicate)."""
    # Insert Kaggle-origin bio (no sofascore_player_id)
    bio_id = repo._player_bios.insert_one({
        "name": "Kenan Yıldız",
        "norm_name": normalize_text("Kenan Yıldız"),
    }).inserted_id
    repo._player_stats.insert_one({
        "player_bio_id": bio_id,
        "season": "2025-2026",
        "team": "Juventus",
        "norm_team": normalize_text("Juventus"),
        "competitions": [],
        "aggregated_stats": _stats_to_empty(),
        "aggregated_scores": _scores_to_empty(),
        "low_sample_size": True,
        "last_updated": datetime.now(timezone.utc).isoformat(),
    })
    assert repo._player_bios.count_documents({"name": "Kenan Yıldız"}) == 1

    p = _make_player("1149011")
    p.name = "Kenan Yıldız"
    p.team = "Juventus"
    repo.upsert_player(p)

    assert repo._player_bios.count_documents({"name": "Kenan Yıldız"}) == 1
    assert repo._player_bios.count_documents({"sofascore_player_id": "1149011"}) == 1
    assert repo._player_stats.count_documents({"season": "2025-2026"}) == 1


def _stats_to_empty() -> dict:
    return {k: 0 for k in [
        "goals", "assists", "xg", "xa", "minutes", "clean_sheets",
        "pk_saved", "pk_won", "pk_scored", "pk_taken", "yellow_cards",
        "red_cards", "fouls_committed", "rating", "big_chances_created", "key_passes",
    ]}


def _scores_to_empty() -> dict:
    return {"offensive": 0.0, "defensive": 0.0, "tactical": 0.0, "s_final": 0.0,
            "sleeper_ratio": None, "sleeper_flag": None}


def test_fetch_state_absent_initially(repo: MongoRepository) -> None:
    assert repo.get_last_fetch() is None


def test_set_and_get_last_fetch_roundtrip(repo: MongoRepository) -> None:
    at = datetime(2026, 6, 12, 9, 30, tzinfo=timezone.utc)
    repo.set_last_fetch("England Premier League", "2025-2026", at)

    state = repo.get_last_fetch()
    assert state is not None
    assert state["last_competition"] == "England Premier League"
    assert state["last_season"] == "2025-2026"
    assert datetime.fromisoformat(state["last_fetched_at"]) == at
    # Singleton: a second write updates rather than inserts a new doc.
    repo.set_last_fetch("Spain La Liga", "2025-2026", at)
    assert repo._fetch_state.count_documents({}) == 1
    assert repo.get_last_fetch()["last_competition"] == "Spain La Liga"
