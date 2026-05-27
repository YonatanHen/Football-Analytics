from abc import ABC, abstractmethod
from app.domain.models import PlayerDTO


class AnalysisMode(ABC):
    @abstractmethod
    def fetch_data(self, season: str, competitions: list[str]) -> dict:
        """Scrape data from sources and upsert to MongoDB. Returns scrape log entry."""

    @abstractmethod
    def process(self, season: str) -> list[PlayerDTO]:
        """Read from MongoDB, apply mode logic, return scored players."""

    @abstractmethod
    def get_mode_name(self) -> str:
        """Return a string identifier for this mode."""
