from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.dependencies import get_mode_factory
from app.modes.factory import ModeFactory
from app.config import settings

router = APIRouter()


class FetchRequest(BaseModel):
    """Body for POST /v1/fetch/. Omit fields to use server defaults from config."""
    season: str | None = None
    mode: str = "fantasy"
    competitions: list[str] | None = None


@router.post("/fetch/", status_code=201)
def trigger_fetch(
    body: FetchRequest,
    mode_factory: ModeFactory = Depends(get_mode_factory),
) -> dict:
    """Trigger a data scrape for the given season and competitions."""
    season = body.season or settings.season
    competitions = body.competitions or settings.default_competitions
    try:
        mode = mode_factory.create(body.mode)
        log = mode.fetch_data(season, competitions)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return log
