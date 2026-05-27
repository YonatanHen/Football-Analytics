from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.dependencies import get_mode_factory
from app.modes.factory import ModeFactory
from app.config import settings

router = APIRouter()


class FetchRequest(BaseModel):
    season: str | None = None
    mode: str = "fantasy"
    competitions: list[str] | None = None


@router.post("/fetch/", status_code=201)
def trigger_fetch(
    body: FetchRequest,
    mode_factory: ModeFactory = Depends(get_mode_factory),
) -> dict:
    season = body.season or settings.season
    competitions = body.competitions or settings.default_competitions
    mode = mode_factory.create(body.mode)
    log = mode.fetch_data(season, competitions)
    return log
