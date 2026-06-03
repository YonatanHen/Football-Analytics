import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import pandas as pd

from app.config import settings
from app.domain.competitions import canonical_competition
from app.domain.player_assembler import build_player, merge
from app.domain.models import Stats, CompetitionEntry
from app.infrastructure.sofascore_client import SofascoreClient
from app.infrastructure.text_utils import normalize_text

logger = logging.getLogger(__name__)

_SS_POSITION_GROUPS = ["Goalkeepers", "Defenders", "Midfielders", "Forwards"]


@dataclass
class FetchJob:
    """In-memory state for a single background fetch operation."""
    id: str
    status: str = "running"       # running | done | partial | error
    total: int = 0
    completed: int = 0
    current: str = ""
    players_upserted: int = 0
    competitions_failed: int = 0
    tasks: list[dict] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)


def _make_tasks(competitions: list[str]) -> list[dict]:
    tasks = []
    for comp in competitions:
        for group in _SS_POSITION_GROUPS:
            tasks.append({"label": f"{comp} — {group}", "status": "pending", "type": "ss", "comp": comp, "group": group})
    return tasks


def _update_task(job: FetchJob, idx: int, status: str) -> None:
    with job.lock:
        job.tasks[idx]["status"] = status
        job.completed += 1


def run_fetch_job(job: FetchJob, season: str, competitions: list[str], repo) -> None:  # type: ignore[type-arg]
    """Execute a parallel fetch job and upsert results.

    Each competition is split into 4 concurrent Sofascore tasks (by position group).
    Competitions themselves also run concurrently up to settings.fetch_concurrency.
    After all scraping, reconciles each player and upserts once (no write races).
    pk_won comes directly from Sofascore's penaltyWon field — FBref is not used.
    """
    sofascore = SofascoreClient()

    tasks = _make_tasks(competitions)
    with job.lock:
        job.tasks = tasks
        job.total = len(tasks)

    results: dict[str, list[pd.DataFrame]] = {comp: [] for comp in competitions}
    failed_comps: set[str] = set()

    def _scrape_ss(task_idx: int, comp: str, group: str) -> None:
        with job.lock:
            job.tasks[task_idx]["status"] = "running"
            job.current = f"{comp} — {group}"
        try:
            df = sofascore.fetch(comp, season, positions=[group])
            with job.lock:
                results[comp].append(df)
            _update_task(job, task_idx, "done")
        except Exception as exc:
            logger.warning("Sofascore fetch failed %s/%s: %s", comp, group, exc)
            with job.lock:
                failed_comps.add(comp)
            _update_task(job, task_idx, "failed")

    futures = []
    with ThreadPoolExecutor(max_workers=settings.fetch_concurrency) as executor:
        for idx, task in enumerate(tasks):
            futures.append(executor.submit(_scrape_ss, idx, task["comp"], task["group"]))
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:
                logger.error("Unexpected task error: %s", exc)

    # Sequential reconciling write pass (no write races)
    from app.domain.scoring_engine import ScoringEngine
    _scoring = ScoringEngine()
    upserted = 0

    for comp in competitions:
        frames = results[comp]
        if not frames:
            failed_comps.add(comp)
            continue
        try:
            ss_df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["sofascore_player_id"])
        except Exception as exc:
            logger.warning("Concat failed for %s: %s", comp, exc)
            failed_comps.add(comp)
            continue

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
                fouls_committed=float(row.get("fouls_committed", 0.0)),
                rating=float(row.get("rating", 0.0)),
                big_chances_created=int(row.get("big_chances_created", 0)),
                key_passes=int(row.get("key_passes", 0)),
            )
            position = str(row.get("position", "MF"))
            score = _scoring.calculate(stats, position)
            entry = CompetitionEntry(competition=canonical_competition(comp), stats=stats, scores=score)
            meta = {
                "sofascore_player_id": pid,
                "name": str(row.get("name", "")),
                "team": str(row.get("team", "")),
                "nationality": str(row.get("nationality", "")),
                "position": position,
                "position_exact": str(row.get("position_exact", "")),
                "photo_url": str(row.get("photo_url", "")),
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
        job.competitions_failed = len(failed_comps)
        job.current = ""
        if len(failed_comps) == len(competitions):
            job.status = "error"
        elif failed_comps:
            job.status = "partial"
        else:
            job.status = "done"
