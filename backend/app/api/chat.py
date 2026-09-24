import logging

from fastapi import APIRouter, Depends, Response

from app.agent.agent import ChatAgent
from app.agent.constants import GENERIC_ERROR
from app.api.modals.chat_modals import ChatHistory, ChatRequest, ChatResponse, ToolCallOut
from app.dependencies import get_agent

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=ChatResponse)
async def chat(body: ChatRequest, agent: ChatAgent | None = Depends(get_agent)) -> ChatResponse:
    """Answer one question. Never surfaces internal errors to the caller."""
    if agent is None:
        return ChatResponse(answer=GENERIC_ERROR, session_id=body.session_id, degraded=True)
    try:
        result = await agent.answer(body.message, session_id=body.session_id)
    except Exception:
        logger.exception("Chat request failed for session %s", body.session_id)
        return ChatResponse(answer=GENERIC_ERROR, session_id=body.session_id, degraded=True)
    return ChatResponse(
        answer=result.answer,
        session_id=body.session_id,
        degraded=result.degraded,
        tool_calls=[ToolCallOut(name=c.name, rows=c.rows) for c in result.tool_calls],
        uncited=result.uncited,
    )


@router.get("/sessions/{session_id}", response_model=ChatHistory)
def get_session(session_id: str, agent: ChatAgent | None = Depends(get_agent)) -> ChatHistory:
    if agent is None:
        return ChatHistory()
    return ChatHistory(turns=agent.history(session_id))


@router.delete("/sessions/{session_id}", status_code=204)
def clear_session(session_id: str, agent: ChatAgent | None = Depends(get_agent)) -> Response:
    if agent is not None:
        agent.clear(session_id)
    return Response(status_code=204)
