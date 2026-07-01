import json
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.modals.player_modals import (
    AggregatedScoresOut,
    BioOut,
    CompetitionOut,
    PlayerListOut,
    PlayerOut,
    ScoreOut,
    StatsOut,
)
from app.config import settings
from app.dependencies import get_repo
from app.domain.metric_fields import FILTER_OPS, METRIC_FIELDS
from app.infrastructure.mongo_repository import MongoRepository
from app.infrastructure.sofascore_client import SofascoreClient

if TYPE_CHECKING:
    from app.domain.models import PlayerDTO

router = APIRouter()


def _err(message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={"error": {"code": "invalid_query", "message": message}},
    )


def _parse_filters(filters: str | None) -> list[dict] | None:
    """Parse and validate the JSON-encoded ``filters`` query param.

    Expects a JSON array of ``{"field", "op", "value"}`` clauses. Each field must be an
    allowlisted metric, each op a known operator, and each value numeric. Raises 422 otherwise.
    """
    if not filters:
        return None
    try:
        clauses = json.loads(filters)
    except json.JSONDecodeError:
        raise _err("filters must be valid JSON.") from None
    if not isinstance(clauses, list):
        raise _err("filters must be a JSON array of clauses.")

    parsed: list[dict] = []
    for c in clauses:
        if not isinstance(c, dict):
            raise _err("Each filter clause must be an object.")
        field, op, value = c.get("field"), c.get("op"), c.get("value")
        if field not in METRIC_FIELDS:
            raise _err(f"Unknown filter field: {field!r}.")
        if op not in FILTER_OPS:
            raise _err(f"Unknown filter operator: {op!r}.")
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise _err(f"Filter value for {field!r} must be numeric.") from None
        parsed.append({"field": field, "op": op, "value": value})
    return parsed


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
                competition_type=c.competition_type,
                stats=StatsOut(**c.stats.__dict__),
                scores=ScoreOut(**c.scores.__dict__),
                raw_stats=c.raw_stats,
                total_matches=c.total_matches,
            )
            for c in p.competitions
        ],
        aggregated_stats=StatsOut(**p.aggregated_stats.__dict__),
        aggregated_scores=AggregatedScoresOut(**p.aggregated_scores.__dict__),
        low_sample_size=p.low_sample_size,
        last_updated=p.last_updated,
    )


@router.get("/competitions")
def list_competitions(
    season: str | None = None,
    repo: MongoRepository = Depends(get_repo),
) -> dict:
    """Return men's competition names from the DB grouped by type.

    Response shape: {"club": [...], "national": [...]}
    """
    return repo.get_competition_list(season or settings.season)


@router.get("")
def list_players(
    position: str | None = Query(None, pattern="^(GK|DF|MF|FW)$"),
    team: str | None = None,
    nationality: str | None = None,
    name: str | None = None,
    underpredicted_flag: str | None = Query(None, pattern="^(HIGH_VALUE|OVERPERFORMING)$"),
    season: str | None = None,
    stats_view: str | None = None,
    sort_by: str = Query("s_final"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    filters: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    repo: MongoRepository = Depends(get_repo),
) -> PlayerListOut:
    """Return a paginated player list with optional filters.

    stats_view: 'all' | 'club' | 'national' | <competition name>
    When set, re-aggregates and re-scores each player from matching competitions only.

    sort_by: any allowlisted metric (see metric_fields.METRIC_FIELDS); defaults to s_final.
    filters: JSON array of {field, op, value} clauses over allowlisted numeric metrics.
    """
    if sort_by not in METRIC_FIELDS:
        raise _err(f"Unknown sort field: {sort_by!r}.")
    parsed_filters = _parse_filters(filters)
    players, total = repo.get_players(
        season=season or settings.season,
        position=position,
        team=team,
        nationality=nationality,
        name=name,
        underpredicted_flag=underpredicted_flag,
        stats_view=stats_view if stats_view and stats_view != "all" else None,
        sort_by=sort_by,
        order=order,
        filters=parsed_filters,
        page=page,
        page_size=page_size,
    )
    return PlayerListOut(
        data=[_to_out(p) for p in players], total=total, page=page, page_size=page_size
    )


@router.get("/{player_id}", response_model=PlayerOut)
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


@router.post("/{player_id}/refresh-bio", response_model=BioOut)
def refresh_player_bio(
    player_id: str,
    repo: MongoRepository = Depends(get_repo),
) -> BioOut:
    """Fetch nationality and position_exact from Sofascore for a single player and persist them.

    Called lazily when a player modal is opened and bio fields are empty.
    Takes ~10s due to Chrome warm-up.
    """
    bio = SofascoreClient().fetch_player_bio(player_id)
    if bio:
        repo.upsert_player_bio(player_id, bio.get("nationality", ""), bio.get("position_exact", ""))
    return BioOut(
        nationality=bio.get("nationality", ""),
        position_exact=bio.get("position_exact", ""),
    )
