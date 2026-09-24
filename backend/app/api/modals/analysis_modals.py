from pydantic import BaseModel


class ScatterPoint(BaseModel):
    """Single player data point for the xG+xA vs G+A scatter chart."""

    sofascore_player_id: str | None
    name: str
    position: str
    team: str = ""
    goals: int = 0
    assists: int = 0
    xg: float = 0.0
    xa: float = 0.0
    minutes: int = 0
    xg_xa: float
    g_a: float
    s_final: float = 0.0
    xratio: float | None = None
    flag: str | None = None


class ScatterDataOut(BaseModel):
    """Response envelope for GET /v1/analysis/scatter."""

    data: list[ScatterPoint]
