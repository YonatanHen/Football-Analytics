from fastapi import APIRouter, Depends

from app.agent.providers import PROVIDERS
from app.api.modals.meta_modals import AgentMetaOut, MetaOut
from app.config import settings
from app.dependencies import get_repo
from app.infrastructure.mongo_repository import MongoRepository

router = APIRouter()


def _model_name() -> str:
    provider = PROVIDERS.get(settings.llm_provider)
    return settings.llm_model or (provider.default_model if provider else "") or "unknown"


@router.get("", response_model=MetaOut)
def get_meta(season: str | None = None, repo: MongoRepository = Depends(get_repo)) -> MetaOut:
    """Player count, last fetch time and stored seasons, plus the chat model settings."""
    season_ = season or settings.season
    return MetaOut(
        players_total=repo.count_players(season_),
        last_updated=repo.last_updated(season_),
        seasons=repo.list_seasons(),
        agent=AgentMetaOut(model=_model_name(), max_tool_calls=settings.agent_max_tool_iterations),
    )
