import pandas as pd

# Maps FBref misc stat column names → our internal names.
# Verify against actual ScraperFC output by inspecting df.columns at runtime.
_FBREF_COLUMN_MAP = {
    "Player": "player_name",
    "Squad": "team",
    "PKwon": "pk_won",
}


class FBrefClient:
    def fetch_misc(self, competition: str, year: int) -> pd.DataFrame:
        from ScraperFC import FBref  # type: ignore[import]  # lazy: triggers network on import
        raw: pd.DataFrame = FBref().scrape_stats(competition, year, "misc")
        return self._normalize(raw)

    def _normalize(self, raw: pd.DataFrame) -> pd.DataFrame:
        present = {k: v for k, v in _FBREF_COLUMN_MAP.items() if k in raw.columns}
        df = raw.rename(columns=present)

        keep = [c for c in ["player_name", "team", "pk_won"] if c in df.columns]
        df = df[keep].copy()

        if "pk_won" in df.columns:
            df["pk_won"] = pd.to_numeric(df["pk_won"], errors="coerce").fillna(0).astype(int)
        else:
            df["pk_won"] = 0

        return df
