from fastapi import APIRouter, Depends

from app.api.modals.analysis_modals import ScatterDataOut, ScatterPoint
from app.config import settings
from app.dependencies import get_repo
from app.infrastructure.mongo_repository import MongoRepository

router = APIRouter()


@router.get("/scatter", response_model=ScatterDataOut)
def scatter_data(
    season: str | None = None,
    repo: MongoRepository = Depends(get_repo),
) -> ScatterDataOut:
    """Return xG+xA vs G+A scatter data points for all players in a season."""
    raw = repo.get_scatter_data(season or settings.season)
    points = []
    for doc in raw:
        agg = doc.get("aggregated_stats", {})
        points.append(
            ScatterPoint(
                sofascore_player_id=doc.get("sofascore_player_id"),
                name=doc.get("name", ""),
                position=doc.get("position", ""),
                xg_xa=float(agg.get("xg", 0)) + float(agg.get("xa", 0)),
                g_a=float(agg.get("goals", 0)) + float(agg.get("assists", 0)),
            )
        )
    return ScatterDataOut(data=points)
