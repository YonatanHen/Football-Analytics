from pydantic import BaseModel


class AgentMetaOut(BaseModel):
    model: str
    max_tool_calls: int


class MetaOut(BaseModel):
    """Dataset status for the app header and the chat header."""

    players_total: int
    last_updated: str | None
    seasons: list[str]
    agent: AgentMetaOut
