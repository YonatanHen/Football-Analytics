from pydantic_settings import BaseSettings


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

    fetch_concurrency: int = 1
    fetch_cooldown_hours: int = 24  # min hours between successful Sofascore league fetches

    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = {"env_file": ".env"}


settings = Settings()
