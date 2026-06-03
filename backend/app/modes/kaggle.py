from pymongo import MongoClient
from app.modes.base import AnalysisMode
from app.domain.models import PlayerDTO
from app.domain.player_assembler import merge
from app.infrastructure.kaggle_client import KaggleDatasetClient
from app.infrastructure.mongo_repository import MongoRepository
from app.infrastructure.text_utils import normalize_text
from app.config import settings


class KaggleMode(AnalysisMode):
    """Loads player data from the Kaggle FBref dataset CSV. Fast offline seed — no live scraping."""

    def __init__(self, mongo_client: MongoClient) -> None:
        self._repo = MongoRepository(mongo_client)
        self._client = KaggleDatasetClient()

    def get_mode_name(self) -> str:
        return "kaggle"

    def fetch_data(self, season: str, competitions: list[str]) -> dict:
        """Download the Kaggle FBref dataset, parse all players, upsert to MongoDB."""
        if not settings.kaggle_api_key:
            raise ValueError("KAGGLE_API_KEY is not set in environment")

        csv_path = self._client.download(settings.kaggle_api_key)
        players = self._client.parse_csv(csv_path, season=season)

        for incoming in players:
            existing = self._repo.find_existing(
                season=season,
                sofascore_player_id=incoming.sofascore_player_id,
                norm_name=normalize_text(incoming.name),
                norm_team=normalize_text(incoming.team),
            )
            self._repo.upsert_player(merge(existing, incoming))

        return self._repo.log_scrape(
            season=season,
            competitions=competitions,
            players_upserted=len(players),
            status="success",
        )

    def process(self, season: str) -> list[PlayerDTO]:
        players, _ = self._repo.get_players(season=season)
        return players
