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
    # Provider and model are configurable; the defaults are Gemini's free tier.
    llm_provider: str = "gemini"
    llm_model: str = ""  # empty means the provider's default model
    llm_api_key: str = ""  # empty means the provider SDK reads its own env var
    llm_fallback_model: str = ""  # empty means no fallback
    gemini_api_key: str = ""
    agent_max_tool_iterations: int = 8
    agent_max_rows: int = 25
    checkpoint_collection: str = "chat_checkpoints"
    chat_session_ttl_seconds: int = 7 * 24 * 60 * 60

    model_config = {"env_file": ".env"}


settings = Settings()
