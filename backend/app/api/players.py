from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.config import settings
from app.dependencies import get_repo
from app.infrastructure.mongo_repository import MongoRepository

if TYPE_CHECKING:
    from app.domain.models import PlayerDTO

router = APIRouter()


class StatsOut(BaseModel):
    """Flat player statistics for one competition or aggregated across all competitions."""

    goals: int
    assists: int
    xg: float
    xa: float
    minutes: int
    clean_sheets: int
    pk_saved: int
    pk_won: int
    pk_scored: int
    pk_taken: int
    yellow_cards: int
    red_cards: int
    fouls_committed: float
    rating: float
    big_chances_created: int
    key_passes: int


class ScoreOut(BaseModel):
    """Fantasy scores broken down by dimension plus the composite s_final."""

    offensive: float
    defensive: float
    tactical: float
    s_final: float


class CompetitionOut(BaseModel):
    """A player's stats and scores for a single competition within a season."""

    competition: str
    stats: StatsOut
    scores: ScoreOut


class AggregatedScoresOut(BaseModel):
    """Season-level fantasy scores including underprediction analysis across all competitions."""

    offensive: float
    defensive: float
    tactical: float
    s_final: float
    underpredicted_ratio: float | None
    underpredicted_flag: str | None


class PlayerOut(BaseModel):
    """Full player profile returned by GET /v1/players/{id} and the players list."""

    sofascore_player_id: str | None
    name: str
    season: str
    position: str
    position_exact: str
    team: str
    nationality: str
    photo_url: str
    competitions: list[CompetitionOut]
    aggregated_stats: StatsOut
    aggregated_scores: AggregatedScoresOut
    low_sample_size: bool
    last_updated: str


class PlayerListOut(BaseModel):
    """Paginated response envelope for GET /v1/players."""

    data: list[PlayerOut]
    total: int
    page: int
    page_size: int


def _to_out(p: "PlayerDTO") -> PlayerOut:
    return PlayerOut(
        sofascore_player_id=p.sofascore_player_id,
        name=p.name,
        season=p.season,
        position=p.position,
        position_exact=p.position_exact,
        team=p.team,
        nationality=p.nationality,
        photo_url=p.photo_url,
        competitions=[
            CompetitionOut(
                competition=c.competition,
                stats=StatsOut(**c.stats.__dict__),
                scores=ScoreOut(**c.scores.__dict__),
            )
            for c in p.competitions
        ],
        aggregated_stats=StatsOut(**p.aggregated_stats.__dict__),
        aggregated_scores=AggregatedScoresOut(**p.aggregated_scores.__dict__),
        low_sample_size=p.low_sample_size,
        last_updated=p.last_updated,
    )


@router.get("/players", response_model=PlayerListOut)
def list_players(
    position: str | None = Query(None, pattern="^(GK|DF|MF|FW)$"),
    team: str | None = None,
    nationality: str | None = None,
    name: str | None = None,
    underpredicted_flag: str | None = Query(None, pattern="^(HIGH_VALUE|OVERPERFORMING)$"),
    season: str | None = None,
    sort_by: str = Query("s_final", pattern="^s_final$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    repo: MongoRepository = Depends(get_repo),
) -> PlayerListOut:
    """Return a paginated player list with optional filters for position, team,
    nationality, name, and underprediction flag."""
    players, total = repo.get_players(
        season=season or settings.season,
        position=position,
        team=team,
        nationality=nationality,
        name=name,
        underpredicted_flag=underpredicted_flag,
        sort_by=sort_by,
        order=order,
        page=page,
        page_size=page_size,
    )
    return PlayerListOut(
        data=[_to_out(p) for p in players], total=total, page=page, page_size=page_size
    )


@router.get("/players/{player_id}", response_model=PlayerOut)
def get_player(
    player_id: str,
    season: str | None = None,
    repo: MongoRepository = Depends(get_repo),
) -> PlayerOut:
    """Return a single player by ID; 404 if not found."""
    season_ = season or settings.season
    player = repo.get_player(player_id, season_)
    if not player:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "Player not found."}},
        )
    return _to_out(player)
