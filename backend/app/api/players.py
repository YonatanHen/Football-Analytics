from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.dependencies import get_repo
from app.infrastructure.mongo_repository import MongoRepository
from app.config import settings

router = APIRouter()


class StatsOut(BaseModel):
    goals: int; assists: int; xg: float; xa: float
    minutes: int; clean_sheets: int; pk_saved: int; pk_won: int
    pk_scored: int; pk_taken: int; yellow_cards: int; red_cards: int
    fouls_committed: float; rating: float; big_chances_created: int; key_passes: int


class ScoreOut(BaseModel):
    offensive: float; defensive: float; tactical: float; s_final: float


class CompetitionOut(BaseModel):
    competition: str; stats: StatsOut; scores: ScoreOut


class AggregatedScoresOut(BaseModel):
    offensive: float; defensive: float; tactical: float; s_final: float
    sleeper_ratio: Optional[float]; sleeper_flag: Optional[str]


class PlayerOut(BaseModel):
    player_id: str; name: str; season: str
    position: str; position_exact: str; team: str; nationality: str
    photo_url: str; competitions: list[CompetitionOut]
    aggregated_stats: StatsOut; aggregated_scores: AggregatedScoresOut
    low_sample_size: bool; last_updated: str


class PlayerListOut(BaseModel):
    data: list[PlayerOut]; total: int; page: int; page_size: int


def _to_out(p: object) -> PlayerOut:
    """Map a PlayerDTO domain object to the API response model."""
    from app.domain.models import PlayerDTO
    assert isinstance(p, PlayerDTO)
    return PlayerOut(
        player_id=p.player_id, name=p.name, season=p.season,
        position=p.position, position_exact=p.position_exact,
        team=p.team, nationality=p.nationality, photo_url=p.photo_url,
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
    position: Optional[str] = Query(None, pattern="^(GK|DF|MF|FW)$"),
    team: Optional[str] = None,
    nationality: Optional[str] = None,
    sleeper_flag: Optional[str] = Query(None, pattern="^(HIGH_VALUE|OVERPERFORMING)$"),
    season: Optional[str] = None,
    sort_by: str = Query("s_final", pattern="^s_final$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    repo: MongoRepository = Depends(get_repo),
) -> PlayerListOut:
    """Return a paginated player list with optional filters for position, team, nationality, and sleeper flag."""
    players, total = repo.get_players(
        season=season or settings.season,
        position=position, team=team, nationality=nationality,
        sleeper_flag=sleeper_flag, sort_by=sort_by, order=order,
        page=page, page_size=page_size,
    )
    return PlayerListOut(data=[_to_out(p) for p in players], total=total, page=page, page_size=page_size)


@router.get("/players/{player_id}", response_model=PlayerOut)
def get_player(
    player_id: str,
    season: Optional[str] = None,
    repo: MongoRepository = Depends(get_repo),
) -> PlayerOut:
    """Return a single player by ID; 404 if not found in the given season."""
    player = repo.get_player(player_id, season or settings.season)
    if not player:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "not_found", "message": "Player not found."}},
        )
    return _to_out(player)
