from app.domain.models import Score, Stats

_POSITION_WEIGHTS: dict[str, dict[str, int]] = {
    "GK": {"goals": 10, "assists": 5},
    "DF": {"goals": 6, "assists": 4},
    "MF": {"goals": 5, "assists": 3},
    "FW": {"goals": 4, "assists": 3},
}


class ScoringEngine:
    def calculate(self, stats: Stats, position: str) -> Score:
        """Compute offensive/defensive/tactical scores and s_final.

        s_final = raw_per90 * starter_bonus + playing_time_bonus
        playing_time_bonus rewards minutes played: 0.01/min up to the 59th minute
        per appearance, 0.015/min from the 60th to 90th minute per appearance.
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

        minutes_per_90 = stats.minutes / 90
        if minutes_per_90 <= 0 or stats.appearances <= 0:
            return Score(offensive=offensive, defensive=defensive, tactical=tactical, s_final=0.0)

        raw_per90 = (offensive + defensive + tactical) / minutes_per_90

        starter_bonus = 1.0 + 0.2 * (stats.matches_started / stats.appearances)

        avg_mins = stats.minutes / stats.appearances
        early_mins = min(avg_mins, 59.0) * stats.appearances
        late_mins = max(0.0, min(avg_mins, 90.0) - 59.0) * stats.appearances
        playing_time_bonus = early_mins * 0.001 + late_mins * 0.0015

        apps = stats.appearances
        if apps < 5:
            confidence = 0.15
        elif apps < 15:
            confidence = 0.50
        elif apps < 20:
            confidence = 0.80
        else:
            confidence = 1.00

        s_final = raw_per90 * starter_bonus * confidence + playing_time_bonus

        return Score(offensive=offensive, defensive=defensive, tactical=tactical, s_final=s_final)
