from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.agent.tools.base import MetricQuery, build_metric_tool, run_metric_query
from app.domain.models import AggregatedScores, CompetitionEntry, PlayerDTO, Score, Stats

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
    assert rows[0]["fantasy_score"] == 5.5
    assert "s_final" not in rows[0]
    assert repo.get_players.call_args.kwargs["sort_by"] == "goals"


def _two_league_player():
    p = _player(goals=36)
    p.competitions = [
        CompetitionEntry("Germany Bundesliga", Stats(goals=30, minutes=2400), Score(0, 0, 0, 0)),
        CompetitionEntry("UEFA Champions League", Stats(goals=6, minutes=700), Score(0, 0, 0, 0)),
    ]
    return p


def test_rows_say_which_season_and_competitions_they_cover():
    rows = run_metric_query(_repo([_two_league_player()]), FAMILY, MetricQuery(metric="goals"))
    assert rows[0]["season"] == "2025-2026"
    assert rows[0]["competitions"] == ["Germany Bundesliga", "UEFA Champions League"]


def test_a_competition_filter_labels_rows_with_that_competition_only():
    repo = _repo([_two_league_player()])
    rows = run_metric_query(repo, FAMILY, MetricQuery(metric="goals", competition="bundesliga"))
    assert rows[0]["competitions"] == ["Germany Bundesliga"]
    assert "by_competition" not in rows[0]
    assert repo.get_players.call_args.kwargs["stats_view"] == "bundesliga"


def test_one_player_across_leagues_gets_the_metric_per_competition():
    repo = _repo([_two_league_player()])
    rows = run_metric_query(repo, FAMILY, MetricQuery(metric="goals", player_name="Kane"))
    assert rows[0]["goals"] == 36  # the combined total
    assert rows[0]["by_competition"] == {"Germany Bundesliga": 30, "UEFA Champions League": 6}


def test_rankings_stay_short_and_have_no_per_competition_split():
    rows = run_metric_query(_repo([_two_league_player()]), FAMILY, MetricQuery(metric="goals"))
    assert "by_competition" not in rows[0]


def test_a_score_metric_per_competition_is_scored_from_that_competition_alone():
    from app.domain.scoring_engine import ScoringEngine

    repo = _repo([_two_league_player()])
    rows = run_metric_query(repo, {"s_final"}, MetricQuery(metric="s_final", player_name="Kane"))
    expected = round(ScoringEngine().calculate(Stats(goals=30, minutes=2400), "FW").s_final, 2)
    assert rows[0]["by_competition"]["Germany Bundesliga"] == expected
    assert "s_final" not in rows[0]  # reported once, as fantasy_score


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
