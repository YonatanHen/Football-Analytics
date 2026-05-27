from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from app.dependencies import get_repo
from app.infrastructure.mongo_repository import MongoRepository
from app.config import settings

router = APIRouter()


class ScatterPoint(BaseModel):
    sofascore_player_id: Optional[str]; name: str; position: str
    xg_xa: float; g_a: float


class ScatterDataOut(BaseModel):
    data: list[ScatterPoint]


@router.get("/analysis/scatter", response_model=ScatterDataOut)
def scatter_data(
    season: Optional[str] = None,
    repo: MongoRepository = Depends(get_repo),
) -> ScatterDataOut:
    """Return xG+xA vs G+A scatter data points for all players in a season."""
    raw = repo.get_scatter_data(season or settings.season)
    points = []
    for doc in raw:
        agg = doc.get("aggregated_stats", {})
        points.append(ScatterPoint(
            sofascore_player_id=doc.get("sofascore_player_id"),
            name=doc.get("name", ""),
            position=doc.get("position", ""),
            xg_xa=float(agg.get("xg", 0)) + float(agg.get("xa", 0)),
            g_a=float(agg.get("goals", 0)) + float(agg.get("assists", 0)),
        ))
    return ScatterDataOut(data=points)
