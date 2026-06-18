from app.domain.models import Score, Stats

_POSITION_WEIGHTS: dict[str, dict[str, int]] = {
    "GK": {"goals": 10, "assists": 5},
    "DF": {"goals": 6, "assists": 4},
    "MF": {"goals": 5, "assists": 3},
    "FW": {"goals": 4, "assists": 3},
}


class ScoringEngine:
    def calculate(self, stats: Stats, position: str, total_possible_minutes: float = 0.0) -> Score:
        """Compute offensive/defensive/tactical scores and s_final.

        total_possible_minutes: sum of (total_matches × 90) across all competitions
            the player appeared in. When 0 (legacy/unknown), playing_time_factor = 1.0.
        """
        weights = _POSITION_WEIGHTS[position]

        offensive = (
            stats.goals * weights["goals"]
            + stats.assists * weights["assists"]
            + stats.xg
            + stats.xa
        )

        if position == "GK":
            defensive = (
                stats.clean_sheets * 5.0
                + stats.pk_saved * 5.0
                + stats.goals_prevented * 2.0
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

        minutes_per_90 = stats.minutes / 90
        if minutes_per_90 <= 0:
            return Score(offensive=offensive, defensive=defensive, tactical=tactical, s_final=0.0)

        raw_per90 = (offensive + defensive + tactical) / minutes_per_90

        if total_possible_minutes > 0:
            playing_time_factor = min(1.0, stats.minutes / total_possible_minutes)
        else:
            playing_time_factor = 1.0  # fallback for legacy records without league_meta

        if stats.appearances > 0:
            starter_bonus = 1.0 + 0.2 * (stats.matches_started / stats.appearances)
        else:
            starter_bonus = 1.0

        s_final = raw_per90 * playing_time_factor * starter_bonus

        return Score(offensive=offensive, defensive=defensive, tactical=tactical, s_final=s_final)
