from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=2000)


class ToolCallOut(BaseModel):
    name: str
    rows: int


# The trace is tool names and row counts only: arguments and row contents never leave the server.
class ChatResponse(BaseModel):
    answer: str
    session_id: str
    degraded: bool = False
    tool_calls: list[ToolCallOut] = []
    uncited: list[str] = []


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatHistory(BaseModel):
    turns: list[ChatTurn] = []
