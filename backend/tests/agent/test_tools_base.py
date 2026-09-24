from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.agent.tools.base import MetricQuery, build_metric_tool, run_metric_query
from app.domain.models import AggregatedScores, PlayerDTO, Stats

FAMILY = {"goals", "assists"}


def _player(name="Player A", goals=10):
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
        aggregated_stats=Stats(goals=goals, assists=3, minutes=900),
        aggregated_scores=AggregatedScores(
            offensive=1,
            defensive=0,
            tactical=0,
            s_final=5.5,
            underpredicted_ratio=None,
            underpredicted_flag=None,
        ),
        low_sample_size=False,
        last_updated="2026-09-02T00:00:00+00:00",
    )


def _repo(players, teams=()):
    repo = MagicMock()
    repo.get_players.return_value = (players, len(players))
    repo.matching_teams.return_value = list(teams)
    return repo


def test_rank_returns_rows_with_the_requested_metric():
    repo = _repo([_player(goals=10), _player("Player B", goals=7)])
    rows = run_metric_query(repo, FAMILY, MetricQuery(metric="goals"))
    assert [r["name"] for r in rows] == ["Player A", "Player B"]
    assert rows[0]["goals"] == 10
    assert rows[0]["s_final"] == 5.5
    assert repo.get_players.call_args.kwargs["sort_by"] == "goals"


def test_unknown_metric_is_rejected_before_reaching_mongo():
    repo = _repo([])
    rows = run_metric_query(repo, FAMILY, MetricQuery(metric="saves"))
    assert rows and "error" in rows[0]
    repo.get_players.assert_not_called()


def test_filter_translates_min_max_into_allowlisted_clauses():
    repo = _repo([_player()])
    run_metric_query(repo, FAMILY, MetricQuery(metric="goals", min_value=5, max_value=20))
    filters = repo.get_players.call_args.kwargs["filters"]
    assert {"field": "goals", "op": "gte", "value": 5.0} in filters
    assert {"field": "goals", "op": "lte", "value": 20.0} in filters


def test_limit_is_capped_by_max_rows():
    from app.agent.constants import MAX_ROWS

    repo = _repo([_player()])
    run_metric_query(repo, FAMILY, MetricQuery(metric="goals", limit=10_000))
    assert repo.get_players.call_args.kwargs["page_size"] == MAX_ROWS


def test_built_tool_exposes_only_its_family_metrics():
    tool = build_metric_tool(
        _repo([]), name="attacking", description="d", metrics=["goals", "assists"]
    )
    assert tool.name == "attacking"
    schema = tool.args_schema.model_json_schema()
    allowed = schema["properties"]["metric"]["enum"]
    assert set(allowed) == {"goals", "assists"}


def test_limit_cannot_disable_the_row_cap():
    # Mongo reads limit(0) as "no limit", which would dump the whole collection.
    for bad in (0, -1):
        with pytest.raises(ValidationError):
            MetricQuery(metric="goals", limit=bad)


def test_lowest_first_questions_can_be_answered():
    # goals_conceded, dribbled_past and errors_lead_to_goal are "lower is better".
    repo = _repo([_player()])
    run_metric_query(repo, FAMILY, MetricQuery(metric="goals", order="asc"))
    assert repo.get_players.call_args.kwargs["order"] == "asc"


def test_sorting_is_highest_first_unless_asked_otherwise():
    repo = _repo([_player()])
    run_metric_query(repo, FAMILY, MetricQuery(metric="goals"))
    assert repo.get_players.call_args.kwargs["order"] == "desc"


def test_the_built_tool_offers_both_sort_directions():
    tool = build_metric_tool(_repo([]), name="attacking", description="d", metrics=["goals"])
    schema = tool.args_schema.model_json_schema()
    assert set(schema["properties"]["order"]["enum"]) == {"asc", "desc"}


def test_an_ambiguous_team_name_is_reported_instead_of_merging_clubs():
    repo = _repo([_player()], teams=["Manchester City", "Manchester United"])
    rows = run_metric_query(repo, FAMILY, MetricQuery(metric="goals", team="Manchester"))
    assert len(rows) == 1
    assert "Manchester City" in rows[0]["error"]
    assert "Manchester United" in rows[0]["error"]
    repo.get_players.assert_not_called()


def test_a_team_name_matching_one_club_still_queries():
    repo = _repo([_player()], teams=["Manchester City"])
    rows = run_metric_query(repo, FAMILY, MetricQuery(metric="goals", team="cit"))
    assert "error" not in rows[0]
    repo.get_players.assert_called_once()


def test_no_team_filter_skips_the_ambiguity_check():
    repo = _repo([_player()])
    rows = run_metric_query(repo, FAMILY, MetricQuery(metric="goals"))
    assert "error" not in rows[0]
    repo.matching_teams.assert_not_called()
