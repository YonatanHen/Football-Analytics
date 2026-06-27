from pydantic import BaseModel


class FetchRequest(BaseModel):
    """Body for POST /v1/fetch/."""

    season: str | None = None
    mode: str = "fantasy"
    competition: str
