from pathlib import Path
from pydantic_settings import BaseSettings


def _read_secret(name: str) -> str:
    path = Path(f"/run/secrets/{name}")
    return path.read_text().strip() if path.exists() else ""


class Settings(BaseSettings):
    mongo_uri: str = "mongodb://localhost:27017/football_analytics"
    season: str = "2025-2026"
    default_competitions: list[str] = [
        "England Premier League",
        "UEFA Champions League",
        "Spain La Liga",
        "Germany Bundesliga",
        "Italy Serie A",
        "France Ligue 1",
    ]

    kaggle_api_key: str = ""

    model_config = {"env_file": ".env"}

    def model_post_init(self, __context: object) -> None:
        if not self.kaggle_api_key:
            self.kaggle_api_key = _read_secret("kaggle_api_key")


settings = Settings()
