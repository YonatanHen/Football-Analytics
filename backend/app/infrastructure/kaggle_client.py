import hashlib
import os
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone
from app.domain.models import (
    PlayerDTO, Stats, Score, CompetitionEntry, AggregatedScores,
)
from app.domain.scoring_engine import ScoringEngine
from app.domain.sleeper_detector import SleeperDetector

_DATASET = "hubertsidorowicz/football-players-stats-2025-2026"

_COMP_MAP = {
    "eng Premier League": "England Premier League",
    "de Bundesliga": "Germany Bundesliga",
    "es La Liga": "Spain La Liga",
    "fr Ligue 1": "France Ligue 1",
    "it Serie A": "Italy Serie A",
}


def _normalize_position(pos: str) -> str:
    primary = str(pos).split(",")[0].strip()
    return primary if primary in ("GK", "DF", "MF", "FW") else "MF"


def _normalize_nationality(nation: str) -> str:
    parts = str(nation).strip().split()
    return parts[-1] if parts else nation


def _player_id(name: str, team: str) -> str:
    return hashlib.md5(f"{name}|{team}".encode()).hexdigest()[:16]


def _int(val) -> int:
    try:
        return int(float(str(val).replace(",", "")))
    except (ValueError, TypeError):
        return 0


def _float(val) -> float:
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def _aggregate_stats(entries: list[CompetitionEntry]) -> Stats:
    total = Stats()
    for e in entries:
        s = e.stats
        total.goals += s.goals
        total.assists += s.assists
        total.minutes += s.minutes
        total.clean_sheets += s.clean_sheets
        total.pk_saved += s.pk_saved
        total.pk_won += s.pk_won
        total.pk_scored += s.pk_scored
        total.pk_taken += s.pk_taken
        total.yellow_cards += s.yellow_cards
        total.red_cards += s.red_cards
        total.fouls_committed += s.fouls_committed
    return total


class KaggleDatasetClient:
    def download(self, api_key: str) -> Path:
        """Download the Kaggle dataset using the provided API token and return path to CSV."""
        os.environ["KAGGLE_TOKEN"] = api_key
        import kagglehub
        dataset_path = kagglehub.dataset_download(_DATASET)
        csv_files = list(Path(dataset_path).rglob("*.csv"))
        if not csv_files:
            raise FileNotFoundError(f"No CSV found in downloaded dataset at {dataset_path}")
        return csv_files[0]

    def parse_csv(self, csv_path: Path, season: str) -> list[PlayerDTO]:
        """Parse the FBref Kaggle CSV into scored PlayerDTOs grouped by player."""
        df = pd.read_csv(csv_path, low_memory=False)
        scoring = ScoringEngine()
        sleeper = SleeperDetector()

        player_entries: dict[str, list[CompetitionEntry]] = {}
        player_meta: dict[str, dict] = {}

        for _, row in df.iterrows():
            name = str(row.get("Player", "")).strip()
            if not name or name == "Player":
                continue

            team = str(row.get("Squad", "")).strip()
            comp_raw = str(row.get("Comp", "")).strip()
            comp = _COMP_MAP.get(comp_raw, comp_raw)
            pos_raw = str(row.get("Pos", "MF")).strip()
            position = _normalize_position(pos_raw)
            pid = _player_id(name, team)

            stats = Stats(
                goals=_int(row.get("Gls", 0)),
                assists=_int(row.get("Ast", 0)),
                minutes=_int(row.get("Min", 0)),
                yellow_cards=_int(row.get("CrdY", 0)),
                red_cards=_int(row.get("CrdR", 0)),
                pk_scored=_int(row.get("PK", 0)),
                pk_taken=_int(row.get("PKatt", 0)),
                clean_sheets=_int(row.get("CS", 0)),
                pk_saved=_int(row.get("PKsv", 0)),
                fouls_committed=_float(row.get("Fls", 0)),
            )
            score = scoring.calculate(stats, position)
            entry = CompetitionEntry(competition=comp, stats=stats, scores=score)

            if pid not in player_entries:
                player_entries[pid] = []
                player_meta[pid] = {
                    "name": name,
                    "team": team,
                    "nationality": _normalize_nationality(str(row.get("Nation", ""))),
                    "position": position,
                    "position_exact": pos_raw,
                }
            player_entries[pid].append(entry)

        now = datetime.now(timezone.utc).isoformat()
        players = []
        for pid, entries in player_entries.items():
            meta = player_meta[pid]
            agg_stats = _aggregate_stats(entries)
            agg_score = scoring.calculate(agg_stats, meta["position"])
            players.append(PlayerDTO(
                sofascore_player_id=None,
                name=meta["name"],
                season=season,
                position=meta["position"],
                position_exact=meta["position_exact"],
                team=meta["team"],
                nationality=meta["nationality"],
                photo_url="",
                competitions=entries,
                aggregated_stats=agg_stats,
                aggregated_scores=AggregatedScores(
                    offensive=agg_score.offensive,
                    defensive=agg_score.defensive,
                    tactical=agg_score.tactical,
                    s_final=agg_score.s_final,
                    sleeper_ratio=sleeper.get_ratio(
                        agg_stats.xg, agg_stats.xa, agg_stats.goals, agg_stats.assists
                    ),
                    sleeper_flag=sleeper.classify(
                        agg_stats.xg, agg_stats.xa,
                        agg_stats.goals, agg_stats.assists, agg_stats.minutes,
                    ),
                ),
                low_sample_size=agg_stats.minutes < 90,
                last_updated=now,
            ))

        return players
