import logging
import time

import pandas as pd

logger = logging.getLogger(__name__)

# Maps ScraperFC Sofascore output column names → our internal names.
_COLUMN_MAP = {
    # Identity
    "player id": "sofascore_player_id",
    "player": "name",
    "team": "team",
    # Core stats
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
    # Appearance
    "appearances": "appearances",
    "matchesStarted": "matches_started",
    # Cards (detailed)
    "yellowRedCards": "yellow_red_cards",
    "directRedCards": "direct_red_cards",
    # GK
    "saves": "saves",
    "savedShotsFromOutsideTheBox": "saves_outside_box",
    "goalsConceded": "goals_conceded",
    "goalsPrevented": "goals_prevented",
    "highClaims": "high_claims",
    "penaltyConceded": "penalty_conceded",
    "penaltyFaced": "penalty_faced",
    # Shots
    "totalShots": "total_shots",
    "shotsOnTarget": "shots_on_target",
    "shotsOffTarget": "shots_off_target",
    "scoringFrequency": "scoring_frequency",
    "attemptPenaltyMiss": "penalty_miss",
    # Goal breakdown
    "headedGoals": "headed_goals",
    "leftFootGoals": "left_foot_goals",
    "rightFootGoals": "right_foot_goals",
}

# Columns promoted to typed Stats fields (plus identity/bio fields)
_TYPED_INTERNAL_NAMES: frozenset[str] = frozenset(_COLUMN_MAP.values()) | {
    "photo_url", "nationality", "position_exact", "position",
}

_POSITION_MAP: dict[str, str] = {
    "G": "GK",
    "GK": "GK",
    "D": "DF",
    "DF": "DF",
    "CB": "DF",
    "LB": "DF",
    "RB": "DF",
    "LWB": "DF",
    "RWB": "DF",
    "M": "MF",
    "MF": "MF",
    "CM": "MF",
    "DM": "MF",
    "AM": "MF",
    "LM": "MF",
    "RM": "MF",
    "F": "FW",
    "FW": "FW",
    "ST": "FW",
    "CF": "FW",
    "LW": "FW",
    "RW": "FW",
    "SS": "FW",
}

_NUMERIC_COLS = [
    "goals", "assists", "xg", "xa", "minutes", "clean_sheets",
    "pk_saved", "pk_won", "pk_scored", "pk_taken",
    "yellow_cards", "red_cards", "yellow_red_cards", "direct_red_cards",
    "fouls_committed", "rating", "big_chances_created", "key_passes",
    "appearances", "matches_started",
    "saves", "saves_outside_box",
    "goals_conceded", "goals_prevented",
    "high_claims", "penalty_conceded", "penalty_faced",
    "total_shots", "shots_on_target", "shots_off_target", "scoring_frequency",
    "penalty_miss",
    "headed_goals", "left_foot_goals", "right_foot_goals",
]


class SofascoreClient:
    """Fetches player league stats from Sofascore via ScraperFC and normalises
    them to internal column names."""

    def fetch_player_bio(self, player_id: str) -> dict:
        """Fetch nationality and position_exact for a single player on demand (lazy bio load).

        Uses XHR via warm Sofascore session. Returns {} on failure.
        """
        from ScraperFC.utils import botasaurus_browser_get_json_via_xhr  # type: ignore[import]

        try:
            url = f"https://api.sofascore.com/api/v1/player/{player_id}"
            data = botasaurus_browser_get_json_via_xhr(url, "https://www.sofascore.com/")
            if not data:
                return {}
            p = data["player"]
            positions_detailed: list[str] = p.get("positionsDetailed") or []
            return {
                "nationality": (p.get("country") or {}).get("name") or "",
                "position_exact": ",".join(positions_detailed),
            }
        except Exception as exc:
            logger.warning("fetch_player_bio: player %s failed: %s", player_id, exc)
            return {}

    def fetch(
        self,
        competition: str,
        season: str,
        positions: list[str] | None = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> pd.DataFrame:
        """Fetch player league stats from Sofascore via ScraperFC and return normalized DataFrame.

        positions: subset of ["Goalkeepers","Defenders","Midfielders","Forwards"]
            for parallel splits.
        Retries up to max_retries times on transient empty-response failures
            (botasaurus concurrency).
        """
        from ScraperFC import Sofascore  # type: ignore[import]  # lazy: triggers network on import

        year = _season_to_sofascore_year(season)
        kwargs: dict = {"year": year, "league": competition}
        if positions is not None:
            kwargs["selected_positions"] = positions

        last_exc: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                raw: pd.DataFrame = Sofascore().scrape_player_league_stats(**kwargs)
                if raw.empty and attempt < max_retries:
                    raise ValueError("Empty response — likely transient botasaurus collision")
                return self._normalize(raw)
            except Exception as exc:
                last_exc = exc
                label = f"{competition}/{positions}"
                logger.warning(
                    "Sofascore attempt %d/%d failed for %s: %s", attempt, max_retries, label, exc
                )
                if attempt < max_retries:
                    time.sleep(retry_delay * attempt)

        raise RuntimeError(f"Sofascore fetch failed after {max_retries} attempts") from last_exc

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

        raw_cols = [c for c in df.columns if c not in _TYPED_INTERNAL_NAMES and not c.startswith("_")]
        if raw_cols:
            df["_raw_stats"] = df[raw_cols].apply(
                lambda row: {k: (None if pd.isna(v) else v) for k, v in row.items()}, axis=1
            )
        else:
            df["_raw_stats"] = [{} for _ in range(len(df))]

        return df


def _season_to_sofascore_year(season: str) -> str:
    """Convert "2025-2026" → "25/26" for ScraperFC Sofascore year format."""
    parts = season.split("-")
    return f"{parts[0][2:]}/{parts[1][2:]}"
