import pandas as pd

_FBREF_COLUMN_MAP = {
    "Player": "player_name",
    "Squad": "team",
    "PKwon": "pk_won",
}


class FBrefClient:
    """Fetches misc stats (penalties won) from FBref via ScraperFC to supplement Sofascore data."""

    def fetch_misc(self, competition: str, season: str) -> pd.DataFrame:
        """Scrape FBref misc stats via ScraperFC and return DataFrame with player_name, team, pk_won."""
        from ScraperFC import FBref  # type: ignore[import]  # lazy: triggers network on import
        result = FBref().scrape_stats(year=season, league=competition, stat_category="misc")
        raw: pd.DataFrame = result.get("player", pd.DataFrame())
        return self._normalize(raw)

    def _normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        """Rename FBref columns to internal names and keep only player_name, team, pk_won."""
        present = {k: v for k, v in _FBREF_COLUMN_MAP.items() if k in raw.columns}
        df = raw.rename(columns=present)

        keep = [c for c in ["player_name", "team", "pk_won"] if c in df.columns]
        df = df[keep].copy()

        if "pk_won" in df.columns:
            df["pk_won"] = pd.to_numeric(df["pk_won"], errors="coerce").fillna(0).astype(int)
        else:
            df["pk_won"] = 0

        return df
