"""Allowlist of sortable/filterable numeric metrics.

Single source of truth for the Rankings dynamic sort & filter feature, and the injection
guard for the ``sort_by`` / ``filters`` query params: any field not present here is rejected
before it can reach a MongoDB query. Every metric maps to a ``(source, attr)`` pair where
``source`` is either ``"stats"`` (field on ``aggregated_stats``) or ``"scores"`` (field on
``aggregated_scores``).
"""

import operator
from dataclasses import fields

from app.domain.models import PlayerDTO, Stats

# Every numeric field on Stats is sortable/filterable via aggregated_stats.<attr>.
_STATS_FIELDS: dict[str, tuple[str, str]] = {f.name: ("stats", f.name) for f in fields(Stats)}

# The four composite scores live on aggregated_scores.
_SCORE_FIELDS: dict[str, tuple[str, str]] = {
    "s_final": ("scores", "s_final"),
    "offensive": ("scores", "offensive"),
    "defensive": ("scores", "defensive"),
    "tactical": ("scores", "tactical"),
}

METRIC_FIELDS: dict[str, tuple[str, str]] = {**_STATS_FIELDS, **_SCORE_FIELDS}

FILTER_OPS: dict[str, str] = {
    "gte": "$gte",
    "lte": "$lte",
    "gt": "$gt",
    "lt": "$lt",
    "eq": "$eq",
    "ne": "$ne",
}

_PY_OPS = {
    "gte": operator.ge,
    "lte": operator.le,
    "gt": operator.gt,
    "lt": operator.lt,
    "eq": operator.eq,
    "ne": operator.ne,
}


def mongo_path(name: str) -> str:
    """Return the MongoDB dotted path for an allowlisted metric name."""
    source, attr = METRIC_FIELDS[name]
    root = "aggregated_stats" if source == "stats" else "aggregated_scores"
    return f"{root}.{attr}"


def python_value(player: PlayerDTO, name: str) -> float:
    """Read a metric value off a PlayerDTO (used by the stats_view re-aggregation path)."""
    source, attr = METRIC_FIELDS[name]
    obj = player.aggregated_stats if source == "stats" else player.aggregated_scores
    return getattr(obj, attr)


def python_matches(player: PlayerDTO, field: str, op: str, value: float) -> bool:
    """Evaluate a single filter clause against a PlayerDTO in Python."""
    return _PY_OPS[op](python_value(player, field), value)
