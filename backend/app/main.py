import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient

from app import dependencies
from app.agent.agent import build_agent
from app.api import analysis, chat, fetch, players
from app.config import settings
from app.infrastructure.mongo_repository import MongoRepository
from app.logging_config import configure_logging
from app.modes.factory import ModeFactory

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    mongo_client = MongoClient(settings.mongo_uri)
    dependencies._repo = MongoRepository(mongo_client)
    dependencies._mode_factory = ModeFactory(mongo_client)
    try:
        dependencies._agent = build_agent(dependencies._repo, mongo_client)
    except Exception:
        # The chatbot is optional: without it the rest of the API must still start.
        logger.warning("Chat agent disabled: could not be built", exc_info=True)
        dependencies._agent = None
    yield
    mongo_client.close()


app = FastAPI(title="Football Analytics API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(fetch.router, prefix="/v1/fetch")
app.include_router(players.router, prefix="/v1/players")
app.include_router(analysis.router, prefix="/v1/analysis")
app.include_router(chat.router, prefix="/v1/chat")


# Re-export for backward compatibility with tests that import from app.main
get_repo = dependencies.get_repo
get_mode_factory = dependencies.get_mode_factory
