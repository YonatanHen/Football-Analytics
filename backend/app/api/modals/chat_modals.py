from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=2000)


# No field can carry a tool trace: tool names, arguments and rows never leave the server.
class ChatResponse(BaseModel):
    answer: str
    session_id: str
    degraded: bool = False


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatHistory(BaseModel):
    turns: list[ChatTurn] = []
