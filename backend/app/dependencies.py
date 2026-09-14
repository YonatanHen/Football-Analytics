from app.agent.agent import ChatAgent
from app.infrastructure.mongo_repository import MongoRepository
from app.modes.factory import ModeFactory

_repo: MongoRepository | None = None
_mode_factory: ModeFactory | None = None
_agent: ChatAgent | None = None


def get_repo() -> MongoRepository:
    assert _repo is not None, "App not started"
    return _repo


def get_mode_factory() -> ModeFactory:
    assert _mode_factory is not None, "App not started"
    return _mode_factory


def get_agent() -> ChatAgent | None:
    """The chat agent, or None when it could not be built (e.g. no GEMINI_API_KEY)."""
    return _agent
