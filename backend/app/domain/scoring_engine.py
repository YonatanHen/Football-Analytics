from app.domain.models import Score, Stats

_POSITION_WEIGHTS: dict[str, dict[str, int]] = {
    "GK": {"goals": 10, "assists": 5},
    "DF": {"goals": 6, "assists": 4},
    "MF": {"goals": 5, "assists": 3},
    "FW": {"goals": 4, "assists": 3},
}


class ScoringEngine:
    def calculate(self, stats: Stats, position: str) -> Score:
        """Return offensive/defensive/tactical scores and S_final for a player."""
        weights = _POSITION_WEIGHTS[position]
        offensive = (
            stats.goals * weights["goals"]
            + stats.assists * weights["assists"]
            + stats.xg
            + stats.xa
        )

        if position == "GK":
            defensive = stats.clean_sheets * 5.0 + stats.pk_saved * 5.0
        elif position == "DF":
            defensive = stats.clean_sheets * 4.0
        else:
            defensive = 0.0

        pk_ratio = (stats.pk_scored / stats.pk_taken * 5) if stats.pk_taken > 0 else 0.0
        tactical = (
            stats.pk_won * 2
            + pk_ratio
            - stats.yellow_cards
            - stats.red_cards * 3
            - stats.fouls_committed * 0.2
        )

        minutes_per_90 = stats.minutes / 90
        s_final = (offensive + defensive + tactical) / minutes_per_90 if minutes_per_90 > 0 else 0.0

        return Score(offensive=offensive, defensive=defensive, tactical=tactical, s_final=s_final)
