"""The chatbot agent: a LangGraph tool-calling loop over the database tools."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial

from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import TypeAdapter, ValidationError

from app.agent.answer_check import uncited_numbers
from app.agent.checkpoints import build_checkpointer, keep_latest_checkpoint
from app.agent.constants import GENERIC_ERROR, MAX_TOOL_ITERATIONS
from app.agent.llm import build_chat_model, build_fallback_model
from app.agent.system_prompt import SYSTEM_PROMPT
from app.agent.tools import build_tools

logger = logging.getLogger(__name__)


@dataclass
class ToolCallSummary:
    name: str
    rows: int


@dataclass
class ChatResult:
    answer: str
    used_tools: bool
    degraded: bool = False
    tool_calls: list[ToolCallSummary] = field(default_factory=list)
    uncited: list[str] = field(default_factory=list)


class ChatAgent:
    def __init__(
        self,
        model: BaseChatModel,
        repo,
        checkpointer,
        fallback_models: list[BaseChatModel] | None = None,
        prune: Callable[[str], None] | None = None,
    ) -> None:
        self._prune = prune
        self._graph = create_agent(
            model=model,
            tools=build_tools(repo),
            system_prompt=SYSTEM_PROMPT,
            checkpointer=checkpointer,
            middleware=[ModelFallbackMiddleware(*fallback_models)] if fallback_models else [],
        )

    def _config(self, session_id: str) -> dict:
        return {
            "configurable": {"thread_id": session_id},
            "recursion_limit": MAX_TOOL_ITERATIONS * 2,
        }

    async def answer(self, message: str, session_id: str) -> ChatResult:
        try:
            # "exit" saves one checkpoint when the turn ends, not one per graph step.
            state = await self._graph.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                config=self._config(session_id),
                durability="exit",
            )
        except Exception:
            logger.exception("Agent failed for session %s", session_id)
            return ChatResult(answer=GENERIC_ERROR, used_tools=False, degraded=True)
        await self._prune_session(session_id)

        messages = _current_turn(state["messages"])
        used_tools = any(isinstance(m, ToolMessage) for m in messages)
        answer = messages[-1].text if messages else ""
        trace = _tool_trace(messages)

        if used_tools and answer:
            rows = _tool_rows(messages)
            uncited = uncited_numbers(answer, rows) if rows is not None else []
            if uncited:
                # A signal, not a gate: withholding the answer would be worse than flagging it.
                logger.warning(
                    "Ungrounded figures %s in answer for session %s; rows=%s",
                    uncited,
                    session_id,
                    rows,
                )
                return ChatResult(
                    answer=answer, used_tools=True, degraded=True, tool_calls=trace, uncited=uncited
                )

        # No tool behind the answer means it is the model's own knowledge, not this app's data.
        return ChatResult(
            answer=answer or GENERIC_ERROR,
            used_tools=used_tools,
            degraded=not (answer and used_tools),
            tool_calls=trace,
        )

    async def _prune_session(self, session_id: str) -> None:
        if self._prune is None:
            return
        try:
            await asyncio.to_thread(self._prune, session_id)
        except Exception:
            # Old checkpoints only cost storage, and the TTL removes them anyway.
            logger.exception("Could not prune checkpoints for session %s", session_id)

    def history(self, session_id: str) -> list[dict]:
        """Replay the thread as {role, content} turns. Tool messages are never exposed."""
        try:
            state = self._graph.get_state(self._config(session_id))
        except Exception:
            logger.exception("Could not read history for session %s", session_id)
            return []
        turns = []
        for m in (state.values or {}).get("messages", []):
            if isinstance(m, HumanMessage):
                turns.append({"role": "user", "content": m.text})
            # Text sent alongside a tool call is the model's preamble; it was never shown.
            elif isinstance(m, AIMessage) and m.text and not m.tool_calls:
                turns.append({"role": "assistant", "content": m.text})
        return turns

    def clear(self, session_id: str) -> None:
        try:
            self._graph.checkpointer.delete_thread(session_id)
        except Exception:
            # The caller gets 204 either way; the TTL removes the thread later.
            logger.exception("Could not clear session %s", session_id)


def _current_turn(messages: list) -> list:
    """Messages after the latest user message; the state holds the whole thread."""
    for i in range(len(messages) - 1, -1, -1):
        if isinstance(messages[i], HumanMessage):
            return messages[i + 1 :]
    return messages


# Rows are heterogeneous by design: a metric row, an identity profile, a coverage object or
# an error row. Validate the shape, not a schema.
_ToolPayload = TypeAdapter(list[dict] | dict)


def _tool_rows(messages) -> list[dict] | None:
    """Rows every tool returned this turn, or None if any output could not be read."""
    rows: list[dict] = []
    for m in messages:
        if not isinstance(m, ToolMessage):
            continue
        try:
            payload = _ToolPayload.validate_json(m.content)
        except ValidationError:
            return None  # unreadable rows would look like missing citations
        rows.extend(payload if isinstance(payload, list) else [payload])
    return rows


def _tool_trace(messages) -> list[ToolCallSummary]:
    """Name and row count of each tool call this turn; arguments are never kept."""
    names = {c["id"]: c["name"] for m in messages if isinstance(m, AIMessage) for c in m.tool_calls}
    trace = []
    for m in messages:
        if not isinstance(m, ToolMessage):
            continue
        try:
            payload = _ToolPayload.validate_json(m.content)
            rows = len(payload) if isinstance(payload, list) else 1
        except ValidationError:
            rows = 0
        trace.append(ToolCallSummary(name=names.get(m.tool_call_id, m.name or "tool"), rows=rows))
    return trace


def build_agent(repo, mongo_client) -> ChatAgent:
    checkpointer = build_checkpointer(mongo_client)
    return ChatAgent(
        model=build_chat_model(),
        repo=repo,
        checkpointer=checkpointer,
        fallback_models=[m for m in [build_fallback_model()] if m],
        prune=partial(keep_latest_checkpoint, checkpointer),
    )
