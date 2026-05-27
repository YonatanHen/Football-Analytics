from pymongo import MongoClient
from app.modes.base import AnalysisMode
from app.modes.fantasy import FantasyMode


class ModeFactory:
    def __init__(self, mongo_client: MongoClient) -> None:
        self._mongo_client = mongo_client

    def create(self, mode: str) -> AnalysisMode:
        if mode == "fantasy":
            return FantasyMode(self._mongo_client)
        raise ValueError(f"Unknown mode: {mode!r}. Available: fantasy")
