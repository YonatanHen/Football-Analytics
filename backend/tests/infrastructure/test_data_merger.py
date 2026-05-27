import pandas as pd
import pytest
from app.infrastructure.data_merger import PlayerDataMerger


@pytest.fixture
def merger() -> PlayerDataMerger:
    return PlayerDataMerger()


def _ss(**kwargs: object) -> pd.DataFrame:
    row: dict = {
        "player_id": "123", "name": "Bukayo Saka", "team": "Arsenal",
        "nationality": "England", "position": "FW", "position_exact": "RW",
        "photo_url": "https://example.com/p.jpg",
        "goals": 5, "assists": 3, "xg": 4.0, "xa": 2.5, "minutes": 900,
        "clean_sheets": 0, "pk_saved": 0, "pk_scored": 1, "pk_taken": 1,
        "yellow_cards": 1, "red_cards": 0, "fouls_committed": 10.0,
        "rating": 7.5, "big_chances_created": 5, "key_passes": 30,
    }
    row.update(kwargs)
    return pd.DataFrame([row])


def _fb(player_name: str = "Bukayo Saka", team: str = "Arsenal", pk_won: int = 2) -> pd.DataFrame:
    return pd.DataFrame([{"player_name": player_name, "team": team, "pk_won": pk_won}])


def test_merge_adds_pk_won(merger: PlayerDataMerger) -> None:
    result = merger.merge(_ss(), _fb(pk_won=2))
    assert result.iloc[0]["pk_won"] == 2


def test_merge_defaults_pk_won_to_zero_on_no_match(merger: PlayerDataMerger) -> None:
    result = merger.merge(_ss(name="Bukayo Saka", team="Arsenal"), _fb("Mohamed Salah", "Liverpool", 3))
    assert result.iloc[0]["pk_won"] == 0


def test_merge_normalizes_names_case_insensitive(merger: PlayerDataMerger) -> None:
    result = merger.merge(_ss(name="bukayo saka"), _fb("BUKAYO SAKA"))
    assert result.iloc[0]["pk_won"] == 2


def test_merge_handles_extra_whitespace(merger: PlayerDataMerger) -> None:
    result = merger.merge(_ss(name="  Bukayo Saka  "), _fb("Bukayo Saka"))
    assert result.iloc[0]["pk_won"] == 2


def test_merge_result_has_all_sofascore_columns(merger: PlayerDataMerger) -> None:
    result = merger.merge(_ss(), _fb())
    for col in ["player_id", "name", "team", "goals", "assists", "xg", "xa", "minutes"]:
        assert col in result.columns


def test_merge_multiple_players(merger: PlayerDataMerger) -> None:
    base = _ss().iloc[0].to_dict()
    ss = pd.DataFrame([
        {**base, "player_id": "1", "name": "Player A", "team": "Arsenal"},
        {**base, "player_id": "2", "name": "Player B", "team": "Chelsea"},
    ])
    fb = pd.DataFrame([
        {"player_name": "Player A", "team": "Arsenal", "pk_won": 1},
        {"player_name": "Player B", "team": "Chelsea", "pk_won": 3},
    ])
    result = merger.merge(ss, fb)
    assert len(result) == 2
    assert result[result["player_id"] == "1"].iloc[0]["pk_won"] == 1
    assert result[result["player_id"] == "2"].iloc[0]["pk_won"] == 3
