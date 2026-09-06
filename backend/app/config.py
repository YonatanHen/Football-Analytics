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

    fetch_concurrency: int = 4

    cors_origins: list[str] = ["http://localhost:5173"]

    # --- chatbot agent ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_fallback_model: str = "gemini-2.0-flash"
    agent_max_tool_iterations: int = 8
    agent_max_rows: int = 25
    checkpoint_collection: str = "chat_checkpoints"

    model_config = {"env_file": ".env"}


settings = Settings()
