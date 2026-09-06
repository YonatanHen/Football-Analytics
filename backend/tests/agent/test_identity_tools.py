from unittest.mock import MagicMock

from app.agent.tools.identity import functions
from app.domain.models import AggregatedScores, PlayerDTO, Stats


def _player(name):
    return PlayerDTO(
        sofascore_player_id="1",
        name=name,
        season="2025-2026",
        position="FW",
        position_exact="ST",
        team="Team A",
        nationality="Portugal",
        photo_url="",
        competitions=[],
        aggregated_stats=Stats(
            goals=12, assists=4, minutes=1200, appearances=15, matches_started=14
        ),
        aggregated_scores=AggregatedScores(
            offensive=8,
            defensive=0,
            tactical=1,
            s_final=7.25,
            underpredicted_ratio=1.4,
            underpredicted_flag="HIGH_VALUE",
        ),
        low_sample_size=False,
        last_updated="2026-09-02T00:00:00+00:00",
    )


def _tools(repo):
    return {t.name: t for t in functions.build(repo)}


def test_find_player_returns_a_profile():
    repo = MagicMock()
    repo.get_players.return_value = ([_player("Player A")], 1)
    out = _tools(repo)["find_player"].invoke({"name": "Player A"})
    assert out[0]["name"] == "Player A"
    assert out[0]["position"] == "FW"
    assert out[0]["sleeper_flag"] == "HIGH_VALUE"


def test_find_player_reports_no_match_without_inventing_one():
    repo = MagicMock()
    repo.get_players.return_value = ([], 0)
    out = _tools(repo)["find_player"].invoke({"name": "Nobody"})
    assert out == []


def test_compare_players_returns_one_row_each():
    repo = MagicMock()
    repo.get_players.side_effect = [([_player("A")], 1), ([_player("B")], 1)]
    out = _tools(repo)["compare_players"].invoke({"first_name": "A", "second_name": "B"})
    assert [r["name"] for r in out] == ["A", "B"]


def test_compare_players_keeps_the_half_it_found():
    # One unknown name must not discard the player that did match.
    repo = MagicMock()
    repo.get_players.side_effect = [([_player("A")], 1), ([], 0)]
    out = _tools(repo)["compare_players"].invoke({"first_name": "A", "second_name": "Nobody"})
    assert [r["name"] for r in out] == ["A"]


def test_data_coverage_reports_competitions_and_seasons():
    repo = MagicMock()
    repo.get_competition_list.return_value = {"club": ["England Premier League"], "national": []}
    repo.list_fetched_leagues.return_value = [
        {"competition": "England Premier League", "season": "2025-2026", "updated_at": "x"}
    ]
    out = _tools(repo)["data_coverage"].invoke({})
    assert "England Premier League" in out["club_competitions"]
    assert out["seasons"] == ["2025-2026"]


def test_a_repository_failure_returns_a_tool_error_not_an_exception():
    from app.agent.constants import TOOL_ERROR

    repo = MagicMock()
    repo.get_players.side_effect = RuntimeError("mongo is down")
    out = _tools(repo)["find_player"].invoke({"name": "Player A"})
    assert out == [{"error": TOOL_ERROR}]


def test_identity_tools_are_registered_in_the_family_list():
    from app.agent.tools import FAMILIES, build_tools

    assert any(f.__name__.endswith("identity") for f in FAMILIES)
    names = [t.name for t in build_tools(MagicMock())]
    assert {"find_player", "compare_players", "data_coverage"} <= set(names)
