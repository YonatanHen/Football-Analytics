import logging
from datetime import datetime, timezone
from pymongo import MongoClient
from app.modes.base import AnalysisMode
from app.domain.models import PlayerDTO
from app.infrastructure.mongo_repository import MongoRepository

logger = logging.getLogger(__name__)


class FantasyMode(AnalysisMode):
    """Live fetch mode: fetches Sofascore + FBref per competition, scores players, and upserts to MongoDB."""

    def __init__(self, mongo_client: MongoClient) -> None:
        self._repo = MongoRepository(mongo_client)

    def get_mode_name(self) -> str:
        return "fantasy"

    def fetch_data(self, season: str, competitions: list[str]) -> dict:
        """Fetch Sofascore+FBref for each competition using the parallel fetch runner."""
        from app.modes.fetch_runner import FetchJob, run_fetch_job
        import uuid
        job = FetchJob(id=str(uuid.uuid4()), total=len(competitions))
        run_fetch_job(job, season, competitions, self._repo)
        log = self._repo.log_fetch(
            season=season,
            competitions=competitions,
            players_upserted=job.players_upserted,
            status="success" if job.status == "done" else job.status,
        )
        log["competitions_failed"] = job.competitions_failed
        return log

    def process(self, season: str) -> list[PlayerDTO]:
        """Return all scored players for the given season from MongoDB."""
        players, _ = self._repo.get_players(season=season)
        return players
