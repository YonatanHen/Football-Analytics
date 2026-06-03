import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

import pandas as pd

from app.config import settings
from app.domain.competitions import canonical_competition
from app.domain.player_assembler import build_player, merge
from app.domain.models import Stats, Score, CompetitionEntry
from app.infrastructure.sofascore_client import SofascoreClient
from app.infrastructure.fbref_client import FBrefClient
from app.infrastructure.data_merger import PlayerDataMerger
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
        tasks.append({"label": f"{comp} — FBref", "status": "pending", "type": "fb", "comp": comp})
    return tasks


def _update_task(job: FetchJob, idx: int, status: str, current_label: str | None = None) -> None:
    with job.lock:
        job.tasks[idx]["status"] = status
        job.completed += 1
        if current_label is not None:
            job.current = current_label


def run_fetch_job(job: FetchJob, season: str, competitions: list[str], repo) -> None:  # type: ignore[type-arg]
    """Execute a parallel fetch job and upsert results.

    Runs SS position-group tasks concurrently up to settings.fetch_concurrency.
    FBref tasks are serialized via a semaphore (headful Chrome + 6s rate limit).
    After all scraping, reconciles each player across competitions and upserts once.
    """
    sofascore = SofascoreClient()
    fbref = FBrefClient()
    merger = PlayerDataMerger()
    fbref_sem = threading.Semaphore(settings.fetch_fbref_concurrency)

    tasks = _make_tasks(competitions)
    with job.lock:
        job.tasks = tasks
        job.total = len(tasks)

    # Collect raw frames per competition: {comp: {"ss": [df, ...], "fb": df}}
    results: dict[str, dict] = {comp: {"ss": [], "fb": pd.DataFrame()} for comp in competitions}
    failed_comps: set[str] = set()

    def _scrape_ss(task_idx: int, comp: str, group: str) -> None:
        with job.lock:
            job.tasks[task_idx]["status"] = "running"
            job.current = f"{comp} — {group}"
        try:
            df = sofascore.fetch(comp, season, positions=[group])
            with job.lock:
                results[comp]["ss"].append(df)
        except Exception as exc:
            logger.warning("Sofascore fetch failed %s/%s: %s", comp, group, exc)
            with job.lock:
                failed_comps.add(comp)
        _update_task(job, task_idx, "done" if comp not in failed_comps else "failed")

    def _scrape_fb(task_idx: int, comp: str) -> None:
        with job.lock:
            job.tasks[task_idx]["status"] = "running"
        with fbref_sem:
            try:
                df = fbref.fetch_misc(comp, season)
                with job.lock:
                    results[comp]["fb"] = df
            except Exception as exc:
                logger.warning("FBref fetch failed %s: %s", comp, exc)
        _update_task(job, task_idx, "done")

    futures = []
    with ThreadPoolExecutor(max_workers=settings.fetch_concurrency) as executor:
        for idx, task in enumerate(tasks):
            if task["type"] == "ss":
                futures.append(executor.submit(_scrape_ss, idx, task["comp"], task["group"]))
            else:
                futures.append(executor.submit(_scrape_fb, idx, task["comp"]))
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception as exc:
                logger.error("Unexpected task error: %s", exc)

    # Sequential reconciling write pass (no write races)
    upserted = 0
    for comp in competitions:
        ss_frames = results[comp]["ss"]
        if not ss_frames:
            failed_comps.add(comp)
            continue
        try:
            ss_df = pd.concat(ss_frames, ignore_index=True).drop_duplicates(subset=["sofascore_player_id"])
            fb_df = results[comp]["fb"]
            merged_df = merger.merge(ss_df, fb_df)
        except Exception as exc:
            logger.warning("Merge failed for %s: %s", comp, exc)
            failed_comps.add(comp)
            continue

        for _, row in merged_df.iterrows():
            pid = str(row.get("sofascore_player_id", "")).strip()
            if not pid:
                continue
            from app.domain.models import Stats as _Stats, Score as _Score, CompetitionEntry as _CE
            stats = _Stats(
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
            from app.domain.scoring_engine import ScoringEngine
            position = str(row.get("position", "MF"))
            score = ScoringEngine().calculate(stats, position)
            entry = _CE(competition=canonical_competition(comp), stats=stats, scores=score)
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
            final_player = merge(existing, incoming)
            repo.upsert_player(final_player)
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
