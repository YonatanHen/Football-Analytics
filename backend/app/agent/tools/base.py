"""Shared args schema and query executor for every metric-family tool."""

import logging
from typing import Literal

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, create_model

from app.agent.constants import MAX_ROWS, TOOL_ERROR
from app.config import settings
from app.domain.metric_fields import METRIC_FIELDS, python_value

logger = logging.getLogger(__name__)


class MetricQuery(BaseModel):
    metric: str
    position: Literal["GK", "DF", "MF", "FW"] | None = None
    team: str | None = None
    nationality: str | None = None
    competition: str | None = Field(None, description="Limit to one competition by name.")
    player_name: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    limit: int = 10


def _row(player, metric: str) -> dict:
    return {
        "name": player.name,
        "team": player.team,
        "position": player.position,
        metric: python_value(player, metric),
        "s_final": round(player.aggregated_scores.s_final, 2),
        "minutes": player.aggregated_stats.minutes,
        "sleeper_flag": player.aggregated_scores.underpredicted_flag,
        "low_sample_size": player.low_sample_size,
    }


def run_metric_query(repo, family: set[str], q: MetricQuery) -> list[dict]:
    if q.metric not in family or q.metric not in METRIC_FIELDS:
        return [{"error": f"{q.metric!r} is not available in this tool."}]

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
            order="desc",
            filters=filters or None,
            page=1,
            page_size=min(q.limit, MAX_ROWS),
        )
    except Exception:
        logger.exception("Tool query failed for metric %s", q.metric)
        return [{"error": TOOL_ERROR}]

    return [_row(p, q.metric) for p in players]


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
