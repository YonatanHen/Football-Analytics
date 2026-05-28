import logging
import uuid
import yaml
from dataclasses import dataclass
from importlib import resources
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies import get_mode_factory
from app.modes.base import AnalysisMode
from app.modes.factory import ModeFactory
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

_jobs: dict[str, "FetchJob"] = {}


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


class FetchRequest(BaseModel):
    """Body for POST /v1/fetch/. Omit fields to use server defaults from config."""
    season: str | None = None
    mode: str = "fantasy"
    competitions: list[str] | None = None


@router.get("/competitions", response_model=list[str])
def list_competitions() -> list[str]:
    """Return all competition names supported by Sofascore fetching."""
    data = resources.files("ScraperFC").joinpath("comps.yaml").read_text()
    comps = yaml.safe_load(data)
    return sorted(k for k, v in comps.items() if "SOFASCORE" in v)


@router.post("/fetch/", status_code=202)
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
        raise HTTPException(status_code=400, detail=str(e))

    job = FetchJob(id=str(uuid.uuid4()), total=len(competitions))
    _jobs[job.id] = job
    background_tasks.add_task(_run_fetch, job, season, competitions, mode)
    return {"job_id": job.id}


@router.get("/fetch/status/{job_id}")
def get_fetch_status(job_id: str) -> dict:
    """Poll the status of a fetch job started by POST /v1/fetch/."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.id,
        "status": job.status,
        "total": job.total,
        "completed": job.completed,
        "current": job.current,
        "players_upserted": job.players_upserted,
        "competitions_failed": job.competitions_failed,
    }


def _run_fetch(job: FetchJob, season: str, competitions: list[str], mode: AnalysisMode) -> None:
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
