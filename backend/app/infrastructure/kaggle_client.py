import hashlib
import os
import pandas as pd
from pathlib import Path
from app.domain.models import PlayerDTO, Stats, Score, CompetitionEntry
from app.domain.scoring_engine import ScoringEngine
from app.domain.competitions import canonical_competition
from app.domain.player_assembler import build_player

_DATASET = "hubertsidorowicz/football-players-stats-2025-2026"


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


class KaggleDatasetClient:
    def download(self, api_key: str) -> Path:
        """Download the Kaggle dataset. Auth via KAGGLE_API_TOKEN env var per kagglehub docs."""
        import kagglesdk.kaggle_env as _kenv
        if not hasattr(_kenv, "get_web_endpoint"):
            _kenv.get_web_endpoint = _kenv.get_endpoint

        os.environ["KAGGLE_API_TOKEN"] = api_key

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

        player_entries: dict[str, list[CompetitionEntry]] = {}
        player_meta: dict[str, dict] = {}

        for _, row in df.iterrows():
            name = str(row.get("Player", "")).strip()
            if not name or name == "Player":
                continue

            team = str(row.get("Squad", "")).strip()
            comp_raw = str(row.get("Comp", "")).strip()
            comp = canonical_competition(comp_raw)
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

        players = []
        for pid, entries in player_entries.items():
            meta = player_meta[pid]
            players.append(build_player(meta, entries, season))

        return players
