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
    """Return one scatter point per player in a season; the client picks the axes."""
    raw = repo.get_scatter_data(season or settings.season)
    points = []
    for doc in raw:
        agg = doc.get("aggregated_stats", {})
        scores = doc.get("aggregated_scores", {})
        xg, xa = float(agg.get("xg", 0)), float(agg.get("xa", 0))
        goals, assists = int(agg.get("goals", 0)), int(agg.get("assists", 0))
        points.append(
            ScatterPoint(
                sofascore_player_id=doc.get("sofascore_player_id"),
                name=doc.get("name", ""),
                position=doc.get("position", ""),
                team=doc.get("team", ""),
                goals=goals,
                assists=assists,
                xg=xg,
                xa=xa,
                minutes=int(agg.get("minutes", 0)),
                xg_xa=xg + xa,
                g_a=goals + assists,
                s_final=float(scores.get("s_final", 0)),
                xratio=scores.get("sleeper_ratio"),
                flag=scores.get("sleeper_flag"),
            )
        )
    return ScatterDataOut(data=points)
