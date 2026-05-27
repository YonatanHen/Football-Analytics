import pandas as pd

# Maps ScraperFC Sofascore column names → our internal names.
# Verify/adjust against actual ScraperFC output by inspecting df.columns at runtime.
_COLUMN_MAP = {
    "id": "player_id",
    "name": "name",
    "team": "team",
    "goals": "goals",
    "goalAssist": "assists",
    "expectedGoals": "xg",
    "expectedAssists": "xa",
    "minutesPlayed": "minutes",
    "cleanSheet": "clean_sheets",
    "savedPenalty": "pk_saved",
    "scoredPenalty": "pk_scored",
    "penaltyTaken": "pk_taken",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "foulCommitted": "fouls_committed",
    "rating": "rating",
    "bigChanceCreated": "big_chances_created",
    "keyPass": "key_passes",
    "playerNationalityName": "nationality",
    "playerPosition": "position_exact",
    "playerPhotoUrl": "photo_url",
}

_POSITION_MAP: dict[str, str] = {
    "G": "GK", "GK": "GK",
    "D": "DF", "DF": "DF", "CB": "DF", "LB": "DF", "RB": "DF", "LWB": "DF", "RWB": "DF",
    "M": "MF", "MF": "MF", "CM": "MF", "DM": "MF", "AM": "MF", "LM": "MF", "RM": "MF",
    "F": "FW", "FW": "FW", "ST": "FW", "CF": "FW", "LW": "FW", "RW": "FW", "SS": "FW",
}

_NUMERIC_COLS = [
    "goals", "assists", "xg", "xa", "minutes", "clean_sheets",
    "pk_saved", "pk_scored", "pk_taken", "yellow_cards", "red_cards",
    "fouls_committed", "rating", "big_chances_created", "key_passes",
]


class SofascoreClient:
    def fetch(self, competition: str, year: int) -> pd.DataFrame:
        """Scrape player league stats from Sofascore via ScraperFC and return normalized DataFrame."""
        from ScraperFC import Sofascore  # type: ignore[import]  # lazy: triggers network on import
        raw: pd.DataFrame = Sofascore().scrape_player_league_stats(competition, year)
        return self._normalize(raw)

    def _normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        """Rename ScraperFC columns to internal names, map positions, and fill nulls."""
        present = {k: v for k, v in _COLUMN_MAP.items() if k in raw.columns}
        df = raw.rename(columns=present)

        if "position_exact" in df.columns:
            df["position"] = df["position_exact"].map(
                lambda p: _POSITION_MAP.get(str(p).upper(), "MF")
            )
        else:
            df["position"] = "MF"

        if "player_id" in df.columns:
            df["player_id"] = df["player_id"].astype(str)

        for col in _NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        for col in ["photo_url", "nationality", "position_exact", "name", "team"]:
            if col not in df.columns:
                df[col] = ""

        return df
