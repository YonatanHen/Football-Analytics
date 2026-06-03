import pandas as pd

# Maps ScraperFC Sofascore output column names → our internal names.
_COLUMN_MAP = {
    "player id": "sofascore_player_id",
    "player": "name",
    "team": "team",
    "goals": "goals",
    "assists": "assists",
    "expectedGoals": "xg",
    "expectedAssists": "xa",
    "minutesPlayed": "minutes",
    "cleanSheet": "clean_sheets",
    "penaltySave": "pk_saved",
    "penaltyWon": "pk_won",
    "penaltyGoals": "pk_scored",
    "penaltiesTaken": "pk_taken",
    "yellowCards": "yellow_cards",
    "redCards": "red_cards",
    "fouls": "fouls_committed",
    "rating": "rating",
    "bigChancesCreated": "big_chances_created",
    "keyPasses": "key_passes",
}

_POSITION_MAP: dict[str, str] = {
    "G": "GK", "GK": "GK",
    "D": "DF", "DF": "DF", "CB": "DF", "LB": "DF", "RB": "DF", "LWB": "DF", "RWB": "DF",
    "M": "MF", "MF": "MF", "CM": "MF", "DM": "MF", "AM": "MF", "LM": "MF", "RM": "MF",
    "F": "FW", "FW": "FW", "ST": "FW", "CF": "FW", "LW": "FW", "RW": "FW", "SS": "FW",
}

_NUMERIC_COLS = [
    "goals", "assists", "xg", "xa", "minutes", "clean_sheets",
    "pk_saved", "pk_won", "pk_scored", "pk_taken", "yellow_cards", "red_cards",
    "fouls_committed", "rating", "big_chances_created", "key_passes",
]


class SofascoreClient:
    """Fetches player league stats from Sofascore via ScraperFC and normalises them to internal column names."""

    def fetch(
        self,
        competition: str,
        season: str,
        positions: list[str] | None = None,
    ) -> pd.DataFrame:
        """Scrape player league stats from Sofascore via ScraperFC and return normalized DataFrame.

        positions: subset of ["Goalkeepers","Defenders","Midfielders","Forwards"] for parallel splits.
        """
        from ScraperFC import Sofascore  # type: ignore[import]  # lazy: triggers network on import
        year = _season_to_sofascore_year(season)
        kwargs: dict = {"year": year, "league": competition}
        if positions is not None:
            kwargs["selected_positions"] = positions
        raw: pd.DataFrame = Sofascore().scrape_player_league_stats(**kwargs)
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

        if "sofascore_player_id" in df.columns:
            df["sofascore_player_id"] = df["sofascore_player_id"].astype(str)

        for col in _NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        for col in ["photo_url", "nationality", "position_exact", "name", "team"]:
            if col not in df.columns:
                df[col] = ""

        return df


def _season_to_sofascore_year(season: str) -> str:
    """Convert "2025-2026" → "25/26" for ScraperFC Sofascore year format."""
    parts = season.split("-")
    return f"{parts[0][2:]}/{parts[1][2:]}"
