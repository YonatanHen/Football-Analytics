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

@router.get("/competitions", response_model=list[str])
def list_competitions() -> list[str]:
    """Return all competition names supported by Sofascore fetching."""
    data = resources.files("ScraperFC").joinpath("comps.yaml").read_text()
    comps = yaml.safe_load(data)
    return sorted(k for k, v in comps.items() if "SOFASCORE" in v)

@router.post("/", status_code=202)
def trigger_fetch(
    body: FetchRequest,
    background_tasks: BackgroundTasks,
    mode_factory: ModeFactory = Depends(get_mode_factory),
) -> dict:
    """Start a background fetch job. Returns job_id immediately for polling."""
    season = body.season or settings.season
    try:
        mode = mode_factory.create(body.mode)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    job = FetchJob(id=str(uuid.uuid4()))
    _jobs[job.id] = job

    if body.mode == "fantasy":
        from app.modes.fantasy import FantasyMode

        if isinstance(mode, FantasyMode):
            background_tasks.add_task(_run_fantasy_fetch, job, season, body.competition, mode._repo)
            return {"job_id": job.id}

    # Non-fantasy modes: fall back to fetch via mode.fetch_data
    background_tasks.add_task(_run_legacy_fetch, job, season, body.competition, mode)
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
            "competition_failed": job.competition_failed,
            "tasks": list(job.tasks),
        }


def _run_fantasy_fetch(
    job: FetchJob, season: str, competition: str, repo: MongoRepository
) -> None:
    run_fetch_job(job, season, competition, repo)
    if job.status == "done":
        repo.set_last_fetch(competition, season, datetime.now(UTC))


def _run_legacy_fetch(
    job: FetchJob, season: str, competition: str, mode: AnalysisMode
) -> None:
    """Fallback for non-fantasy modes."""
    job.total = 1
    job.current = competition
    try:
        result = mode.fetch_data(season, competition)
        job.players_upserted = result.get("players_upserted", 0)
        job.status = "error" if result.get("competition_failed", False) else "done"
    except Exception as exc:
        logger.error("Fetch failed for %s: %s", competition, exc)
        job.status = "error"
    job.completed = 1
    job.current = ""
    job.competition_failed = job.status == "error"
