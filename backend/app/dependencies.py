from app.infrastructure.mongo_repository import MongoRepository
from app.modes.factory import ModeFactory

_repo: MongoRepository | None = None
_mode_factory: ModeFactory | None = None


def get_repo() -> MongoRepository:
    assert _repo is not None, "App not started"
    return _repo


def get_mode_factory() -> ModeFactory:
    assert _mode_factory is not None, "App not started"
    return _mode_factory
