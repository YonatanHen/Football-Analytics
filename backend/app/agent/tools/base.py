"""Shared args schema and query executor for every metric-family tool."""

import logging
from typing import Literal

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, create_model

from app.agent.constants import MAX_ROWS, TOOL_ERROR
from app.config import settings
from app.domain.competitions import canonical_competition
from app.domain.metric_fields import METRIC_FIELDS, python_value
from app.domain.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)

_SCORING = ScoringEngine()


class MetricQuery(BaseModel):
    metric: str
    position: Literal["GK", "DF", "MF", "FW"] | None = None
    team: str | None = None
    nationality: str | None = None
    competition: str | None = Field(None, description="Limit to one competition by name.")
    player_name: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    order: Literal["desc", "asc"] = Field(
        "desc", description="desc ranks highest first; asc for 'fewest' or 'least' questions."
    )
    limit: int = Field(10, ge=1, description="How many rows to return.")


def entries_in_scope(player, competition: str | None) -> list:
    """The player's competition entries behind the row: one if filtered, else all."""
    if not competition:
        return list(player.competitions)
    if competition in ("club", "national"):  # the repository's two group views
        return [e for e in player.competitions if e.competition_type == competition]
    target = canonical_competition(competition)
    return [e for e in player.competitions if e.competition == target]


def competition_value(entry, position: str, metric: str) -> float:
    """A metric for one competition; scores are recomputed from that competition's stats."""
    source, attr = METRIC_FIELDS[metric]
    if source == "stats":
        return getattr(entry.stats, attr)
    return round(getattr(_SCORING.calculate(entry.stats, position), attr), 2)


def _row(player, metric: str, q: MetricQuery) -> dict:
    entries = entries_in_scope(player, q.competition)
    row = {
        "name": player.name,
        "team": player.team,
        "position": player.position,
        "season": player.season,
        "competitions": [e.competition for e in entries],
        "fantasy_score": round(player.aggregated_scores.s_final, 2),
        "minutes": player.aggregated_stats.minutes,
        "sleeper_flag": player.aggregated_scores.underpredicted_flag,
        "low_sample_size": player.low_sample_size,
    }
    if metric != "s_final":  # already there as fantasy_score
        row[metric] = python_value(player, metric)
    # Only for a named player: a per-league split on every ranking row would bloat answers.
    if q.player_name and not q.competition and len(entries) > 1:
        row["by_competition"] = {
            e.competition: competition_value(e, player.position, metric) for e in entries
        }
    return row


def run_metric_query(repo, family: set[str], q: MetricQuery) -> list[dict]:
    if q.metric not in family or q.metric not in METRIC_FIELDS:
        return [{"error": f"{q.metric!r} is not available in this tool."}]

    if q.team:
        # The team filter matches by substring, so "Manchester" would merge City and United.
        teams = repo.matching_teams(settings.season, q.team)
        if len(teams) > 1:
            return [{"error": f"{q.team!r} matches {teams}. Ask again with one full team name."}]

    filters: list[dict] = []
    if q.min_value is not None:
        filters.append({"field": q.metric, "op": "gte", "value": float(q.min_value)})
    if q.max_value is not None:
        filters.append({"field": q.metric, "op": "lte", "value": float(q.max_value)})

    try:
        players, _ = repo.get_players(
            season=settings.season,
            position=q.position,
            team=q.team,
            nationality=q.nationality,
            name=q.player_name,
            stats_view=q.competition,
            sort_by=q.metric,
            order=q.order,
            filters=filters or None,
            page=1,
            page_size=min(q.limit, MAX_ROWS),
        )
    except Exception:
        logger.exception("Tool query failed for metric %s", q.metric)
        return [{"error": TOOL_ERROR}]

    return [_row(p, q.metric, q) for p in players]


def build_metric_tool(repo, *, name: str, description: str, metrics: list[str]) -> BaseTool:
    """Build one family tool whose `metric` argument is restricted to `metrics`."""
    family = set(metrics)
    args_schema = create_model(
        f"{name.title().replace('_', '')}Args",
        __base__=MetricQuery,
        metric=(Literal[tuple(metrics)], ...),  # type: ignore[valid-type]
    )

    def _run(**kwargs) -> list[dict]:
        return run_metric_query(repo, family, MetricQuery(**kwargs))

    return StructuredTool.from_function(
        func=_run, name=name, description=description, args_schema=args_schema
    )
