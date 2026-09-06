"""Promote Sofascore defensive columns from raw_stats into the typed Stats model.

raw_stats is the single source for these, so a live fetch and the backfill migration
share one mapping. Rates are derived from counts, never read from Sofascore's own
percentage columns, so they stay correct once counts are summed across competitions.
"""

from app.domain.models import Stats

DEFENSIVE_RAW_MAP: dict[str, str] = {
    "tackles": "tackles",
    "tacklesWon": "tackles_won",
    "interceptions": "interceptions",
    "clearances": "clearances",
    "outfielderBlocks": "blocks",
    "aerialDuelsWon": "aerial_duels_won",
    "aerialLost": "aerial_lost",
    "ballRecovery": "ball_recoveries",
    "dribbledPast": "dribbled_past",
    "errorLeadToGoal": "errors_lead_to_goal",
    "errorLeadToShot": "errors_lead_to_shot",
}


def apply_defensive_raw(stats: Stats, raw: dict | None) -> Stats:
    """Copy the defensive columns out of one entry's raw_stats onto stats, then derive rates."""
    for raw_key, field in DEFENSIVE_RAW_MAP.items():
        value = (raw or {}).get(raw_key)
        if value is None:
            continue
        try:
            setattr(stats, field, int(float(value)))
        except (TypeError, ValueError):
            continue
    recompute_rates(stats)
    return stats


def recompute_rates(stats: Stats) -> Stats:
    """Derive success rates from the current counts. Safe to call after aggregation."""
    stats.tackles_won_pct = _pct(stats.tackles_won, stats.tackles)
    stats.aerial_duels_won_pct = _pct(
        stats.aerial_duels_won, stats.aerial_duels_won + stats.aerial_lost
    )
    return stats


def _pct(won: float, attempted: float) -> float:
    return round(won / attempted * 100, 1) if attempted > 0 else 0.0
