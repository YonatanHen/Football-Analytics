import logging

from pymongo import MongoClient

from app.domain.models import PlayerDTO
from app.infrastructure.mongo_repository import MongoRepository
from app.modes.base import AnalysisMode

logger = logging.getLogger(__name__)


class FantasyMode(AnalysisMode):
    """Live fetch mode: fetches Sofascore per competition, scores players, and
    upserts to MongoDB."""

    def __init__(self, mongo_client: MongoClient) -> None:
        self._repo = MongoRepository(mongo_client)

    def get_mode_name(self) -> str:
        return "fantasy"

    def fetch_data(self, season: str, competition: str) -> dict:
        """Fetch Sofascore data for the given competition using the parallel fetch runner."""
        import uuid

        from app.modes.fetch_runner import FetchJob, run_fetch_job

        job = FetchJob(id=str(uuid.uuid4()))
        run_fetch_job(job, season, competition, self._repo)
        log = self._repo.log_fetch(
            season=season,
            competition=competition,
            players_upserted=job.players_upserted,
            status="success" if job.status == "done" else job.status,
        )
        log["competition_failed"] = job.status == "error"
        return log

    def process(self, season: str) -> list[PlayerDTO]:
        """Return all scored players for the given season from MongoDB."""
        players, _ = self._repo.get_players(season=season)
        return players
