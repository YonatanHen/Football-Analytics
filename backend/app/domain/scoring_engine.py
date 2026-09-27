import math

from app.domain.models import Score, Stats

_POSITION_WEIGHTS: dict[str, dict[str, int]] = {
    "GK": {"goals": 10, "assists": 5},
    "DF": {"goals": 6, "assists": 4},
    "MF": {"goals": 5, "assists": 3},
    "FW": {"goals": 4, "assists": 3},
}


def effective_appearances(stats: Stats) -> int:
    """Appearance count, estimated as ceil(minutes/90) when missing or non-positive."""
    # ceil, not round: round can imply >90 min per appearance (1300 min -> 14 apps).
    return stats.appearances if stats.appearances > 0 else math.ceil(stats.minutes / 90)


def confidence_tier(apps: int) -> float:
    """Confidence multiplier: 0.15/0.50/0.80/1.00 for <5/5-14/15-19/20+ appearances."""
    if apps < 5:
        return 0.15
    if apps < 15:
        return 0.50
    if apps < 20:
        return 0.80
    return 1.00


ELITE_RAW = 8.0  # raw score that maps to 10; fixed, never derived from the data
MAX_SCORE = 10.0


def playing_time_bonus(stats: Stats, apps: int) -> float:
    """0-1 bonus from average minutes per appearance: 0.5 for the first 59, 0.5 for 60-90."""
    avg = stats.minutes / apps
    early = min(avg, 59.0) / 59.0
    late = max(0.0, min(avg, 90.0) - 59.0) / 31.0
    return 0.5 * early + 0.5 * late


def to_fantasy_scale(raw: float) -> float:
    return min(MAX_SCORE, max(0.0, MAX_SCORE * raw / ELITE_RAW))


class ScoringEngine:
    def calculate(self, stats: Stats, position: str) -> Score:
        """Compute the three pillars and s_final, a 0-10 score from this player's stats only."""
        weights = _POSITION_WEIGHTS[position]

        offensive = (
            stats.goals * weights["goals"]
            + stats.assists * weights["assists"]
            + stats.xg
            + stats.xa
        )

        if position == "GK":
            defensive = (
                stats.clean_sheets * 5.0 + stats.pk_saved * 5.0 + stats.goals_prevented * 2.0
            )
        elif position == "DF":
            defensive = stats.clean_sheets * 4.0
        else:
            defensive = 0.0

        pk_ratio = (stats.pk_scored / stats.pk_taken * 5) if stats.pk_taken > 0 else 0.0
        tactical = (
            stats.pk_won * 2
            + pk_ratio
            - stats.yellow_cards
            - stats.yellow_red_cards * 2
            - stats.direct_red_cards * 4
            - stats.fouls_committed * 0.2
        )

        if stats.minutes <= 0:
            return Score(offensive=offensive, defensive=defensive, tactical=tactical, s_final=0.0)

        apps = effective_appearances(stats)
        # Floor of one full match: a card in 1 minute must not become -90 per 90.
        raw_per90 = (offensive + defensive + tactical) / max(stats.minutes / 90, 1.0)
        starter_bonus = 1.0 + 0.2 * min(1.0, stats.matches_started / apps)
        raw = raw_per90 * starter_bonus * confidence_tier(apps) + playing_time_bonus(stats, apps)

        return Score(
            offensive=offensive,
            defensive=defensive,
            tactical=tactical,
            s_final=to_fantasy_scale(raw),
        )
