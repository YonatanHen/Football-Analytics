from pydantic import BaseModel


class FetchRequest(BaseModel):
    """Body for POST /v1/fetch/. Omit fields to use server defaults from config."""

    season: str | None = None
    mode: str = "fantasy"
    competitions: list[str] | None = None
