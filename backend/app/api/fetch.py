import logging
import uuid
from datetime import UTC, datetime
from importlib import resources

import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.modals.fetch_modals import FetchRequest
from app.config import settings
from app.dependencies import get_mode_factory, get_repo
from app.domain.fetch_cooldown import cooldown_status
from app.infrastructure.mongo_repository import MongoRepository
from app.modes.base import AnalysisMode
from app.modes.factory import ModeFactory
from app.modes.fetch_runner import FetchJob, run_fetch_job

router = APIRouter()
logger = logging.getLogger(__name__)

_jobs: dict[str, FetchJob] = {}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _cooldown_payload(repo: MongoRepository) -> dict:
    """Compute the current cooldown state for the UI / enforcement."""
    state = repo.get_last_fetch()
    raw = state.get("last_fetched_at") if state else None
    last = datetime.fromisoformat(raw) if raw else None
    status = cooldown_status(last, datetime.now(UTC), settings.fetch_cooldown_hours)
    return {
        "allowed": status["allowed"],
        "cooldown_hours": settings.fetch_cooldown_hours,
        "last_fetched_at": _iso(status["last_fetched_at"]),
        "next_allowed_at": _iso(status["next_allowed_at"]),
        "seconds_remaining": status["seconds_remaining"],
        "last_competition": state.get("last_competition") if state else None,
    }


@router.get("/competitions", response_model=list[str])
def list_competitions() -> list[str]:
    """Return all competition names supported by Sofascore fetching."""
    data = resources.files("ScraperFC").joinpath("comps.yaml").read_text()
    comps = yaml.safe_load(data)
    return sorted(k for k, v in comps.items() if "SOFASCORE" in v)


@router.get("/cooldown")
def get_cooldown(repo: MongoRepository = Depends(get_repo)) -> dict:
    """Report whether a Sofascore league fetch is currently allowed and when the next one is."""
    return _cooldown_payload(repo)


@router.post("/", status_code=202)
def trigger_fetch(
    body: FetchRequest,
    background_tasks: BackgroundTasks,
    mode_factory: ModeFactory = Depends(get_mode_factory),
) -> dict:
    """Start a background fetch job. Returns job_id immediately for polling."""
    season = body.season or settings.season
    competitions = body.competitions or settings.default_competitions
    try:
        mode = mode_factory.create(body.mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    job = FetchJob(id=str(uuid.uuid4()))
    _jobs[job.id] = job

    if body.mode == "fantasy":
        from app.modes.fantasy import FantasyMode

        if isinstance(mode, FantasyMode):
            background_tasks.add_task(_run_fantasy_fetch, job, season, competitions, mode._repo)
            return {"job_id": job.id}

    # Non-fantasy modes: fall back to sequential fetch via mode.fetch_data
    background_tasks.add_task(_run_legacy_fetch, job, season, competitions, mode)
    return {"job_id": job.id}


@router.get("/status/{job_id}")
def get_fetch_status(job_id: str) -> dict:
    """Poll the status of a fetch job started by POST /v1/fetch/."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    with job.lock:
        return {
            "job_id": job.id,
            "status": job.status,
            "total": job.total,
            "completed": job.completed,
            "current": job.current,
            "players_upserted": job.players_upserted,
            "competitions_failed": job.competitions_failed,
            "tasks": list(job.tasks),
        }


def _run_fantasy_fetch(
    job: FetchJob, season: str, competitions: list[str], repo: MongoRepository
) -> None:
    run_fetch_job(job, season, competitions, repo)
    # Start the cooldown only when data actually landed — a 403/failed fetch must
    # not lock the user out.
    if job.status in ("done", "partial"):
        comp = competitions[0] if competitions else ""
        repo.set_last_fetch(comp, season, datetime.now(UTC))


def _run_legacy_fetch(
    job: FetchJob, season: str, competitions: list[str], mode: AnalysisMode
) -> None:
    """Sequential fallback for non-fantasy modes."""
    job.total = len(competitions)
    for comp in competitions:
        job.current = comp
        try:
            result = mode.fetch_data(season, [comp])
            job.players_upserted += result.get("players_upserted", 0)
            if result.get("competitions_failed", 0) > 0:
                job.competitions_failed += 1
        except Exception as exc:
            logger.error("Fetch failed for %s: %s", comp, exc)
            job.competitions_failed += 1
        job.completed += 1

    job.current = ""
    if job.competitions_failed == job.total:
        job.status = "error"
    elif job.competitions_failed > 0:
        job.status = "partial"
    else:
        job.status = "done"
