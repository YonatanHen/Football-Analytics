from pydantic import BaseModel


class ScatterPoint(BaseModel):
    """Single player data point for the xG+xA vs G+A scatter chart."""

    sofascore_player_id: str | None
    name: str
    position: str
    xg_xa: float
    g_a: float


class ScatterDataOut(BaseModel):
    """Response envelope for GET /v1/analysis/scatter."""

    data: list[ScatterPoint]
