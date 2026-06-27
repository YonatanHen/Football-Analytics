import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import pandas as pd

from app.config import settings
from app.domain.competitions import canonical_competition, classify_competition
from app.domain.models import CompetitionEntry, Stats
from app.domain.player_assembler import build_player, merge
from app.infrastructure.sofascore_client import SofascoreClient
from app.infrastructure.text_utils import normalize_text

logger = logging.getLogger(__name__)


@dataclass
class FetchJob:
    """In-memory state for a single background fetch operation."""

    id: str
    status: str = "running"  # running | done | error
    total: int = 0
    completed: int = 0
    current: str = ""
    players_upserted: int = 0
    competition_failed: bool = False
    tasks: list[dict] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


_POSITION_GROUPS = ["Goalkeepers", "Defenders", "Midfielders", "Forwards"]

_GROUP_TO_POSITION: dict[str, str] = {
    "Goalkeepers": "GK",
    "Defenders": "DF",
    "Midfielders": "MF",
    "Forwards": "FW",
}


def _make_tasks(competition: str) -> list[dict]:
    return [
        {
            "label": f"{competition} — {pos}",
            "status": "pending",
            "type": "ss",
            "comp": competition,
            "positions": [pos],
        }
        for pos in _POSITION_GROUPS
    ]


def _update_task(job: FetchJob, idx: int, status: str) -> None:
    with job.lock:
        job.tasks[idx]["status"] = status
        job.completed += 1


def run_fetch_job(job: FetchJob, season: str, competition: str, repo) -> None:  # type: ignore[type-arg]
    """Execute a fetch job and upsert results.

    The competition is fetched once per position group (GK/DF/MF/FW), so four Sofascore
    calls in total. Tasks run concurrently up to settings.fetch_concurrency. After all
    fetching, frames are concatenated (deduped by sofascore_player_id) and upserted
    sequentially (no write races).
    """
    sofascore = SofascoreClient()

    tasks = _make_tasks(competition)
    with job.lock:
        job.tasks = tasks
        job.total = len(tasks)

    frames: list[pd.DataFrame] = []
    fetch_failed = False

    def _fetch_ss(task_idx: int, positions: list[str]) -> None:
        with job.lock:
            job.tasks[task_idx]["status"] = "running"
            job.current = f"{competition} — {positions[0]}"
        try:
            df = sofascore.fetch(competition, season, positions=positions)
            df["_position_group"] = _GROUP_TO_POSITION.get(positions[0], "MF")
            with job.lock:
                frames.append(df)
            _update_task(job, task_idx, "done")
        except Exception as exc:
            logger.warning("Sofascore fetch failed %s %s: %s", competition, positions, exc)
            _update_task(job, task_idx, "failed")

    futures = []
    with ThreadPoolExecutor(max_workers=settings.fetch_concurrency) as executor:
        for idx, task in enumerate(tasks):
            futures.append(executor.submit(_fetch_ss, idx, task["positions"]))
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:
                logger.error("Unexpected task error: %s", exc)

    # Sequential reconciling write pass (no write races)
    from app.domain.scoring_engine import ScoringEngine

    _scoring = ScoringEngine()
    upserted = 0

    if not frames:
        fetch_failed = True
    else:
        try:
            ss_df = pd.concat(frames, ignore_index=True).drop_duplicates(
                subset=["sofascore_player_id"]
            )
        except Exception as exc:
            logger.warning("Concat failed for %s: %s", competition, exc)
            fetch_failed = True
            ss_df = pd.DataFrame()

        if not fetch_failed:
            total_matches = (
                int(ss_df["appearances"].max())
                if "appearances" in ss_df.columns and not ss_df["appearances"].empty
                else 0
            )
            repo.set_league_total_matches(competition, season, total_matches)

            for _, row in ss_df.iterrows():
                pid = str(row.get("sofascore_player_id", "")).strip()
                if not pid:
                    continue
                stats = Stats(
                    goals=int(row.get("goals", 0)),
                    assists=int(row.get("assists", 0)),
                    xg=float(row.get("xg", 0.0)),
                    xa=float(row.get("xa", 0.0)),
                    minutes=int(row.get("minutes", 0)),
                    clean_sheets=int(row.get("clean_sheets", 0)),
                    pk_saved=int(row.get("pk_saved", 0)),
                    pk_won=int(row.get("pk_won", 0)),
                    pk_scored=int(row.get("pk_scored", 0)),
                    pk_taken=int(row.get("pk_taken", 0)),
                    yellow_cards=int(row.get("yellow_cards", 0)),
                    red_cards=int(row.get("red_cards", 0)),
                    yellow_red_cards=int(row.get("yellow_red_cards", 0)),
                    direct_red_cards=int(row.get("direct_red_cards", 0)),
                    fouls_committed=float(row.get("fouls_committed", 0.0)),
                    rating=float(row.get("rating", 0.0)),
                    big_chances_created=int(row.get("big_chances_created", 0)),
                    key_passes=int(row.get("key_passes", 0)),
                    appearances=int(row.get("appearances", 0)),
                    matches_started=int(row.get("matches_started", 0)),
                    saves=int(row.get("saves", 0)),
                    saves_outside_box=int(row.get("saves_outside_box", 0)),
                    goals_conceded=int(row.get("goals_conceded", 0)),
                    goals_prevented=float(row.get("goals_prevented", 0.0)),
                    high_claims=int(row.get("high_claims", 0)),
                    penalty_conceded=int(row.get("penalty_conceded", 0)),
                    penalty_faced=int(row.get("penalty_faced", 0)),
                    total_shots=int(row.get("total_shots", 0)),
                    shots_on_target=int(row.get("shots_on_target", 0)),
                    shots_off_target=int(row.get("shots_off_target", 0)),
                    scoring_frequency=float(row.get("scoring_frequency", 0.0)),
                    penalty_miss=int(row.get("penalty_miss", 0)),
                    headed_goals=int(row.get("headed_goals", 0)),
                    left_foot_goals=int(row.get("left_foot_goals", 0)),
                    right_foot_goals=int(row.get("right_foot_goals", 0)),
                )
                position = str(row.get("_position_group") or row.get("position", "MF"))
                score = _scoring.calculate(stats, position)
                raw_stats = row.get("_raw_stats") or {}
                if not isinstance(raw_stats, dict):
                    raw_stats = {}
                canon = canonical_competition(competition)
                entry = CompetitionEntry(
                    competition=canon,
                    stats=stats,
                    scores=score,
                    raw_stats=raw_stats,
                    total_matches=total_matches,
                    competition_type=classify_competition(canon),
                )
                meta = {
                    "sofascore_player_id": pid,
                    "name": str(row.get("name", "")),
                    "team": str(row.get("team", "")),
                    "nationality": "",
                    "position": position,
                    "position_exact": "",
                    "photo_url": "",
                }
                incoming = build_player(meta, [entry], season)
                existing = repo.find_existing(
                    season=season,
                    sofascore_player_id=pid,
                    norm_name=normalize_text(meta["name"]),
                    norm_team=normalize_text(meta["team"]),
                )
                repo.upsert_player(merge(existing, incoming))
                upserted += 1

    with job.lock:
        job.players_upserted = upserted
        job.competition_failed = fetch_failed
        job.current = ""
        job.status = "error" if fetch_failed else "done"
