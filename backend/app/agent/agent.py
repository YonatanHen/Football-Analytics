"""The chatbot agent: a LangGraph tool-calling loop over the database tools."""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass
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
from app.agent.web_fallback import web_answer

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    answer: str
    used_tools: bool
    degraded: bool = False


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

    async def answer(self, message: str, session_id: str, allow_web: bool = True) -> ChatResult:
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

        messages = state["messages"]
        used_tools = any(isinstance(m, ToolMessage) for m in messages)
        answer = messages[-1].text if messages else ""

        # No tool produced data, so the answer is ungrounded. Prefer a labelled web answer
        # over the model's own guess; degraded marks it as not from the app's data.
        if allow_web and not used_tools:
            grounded = await web_answer(message)
            if grounded:
                return ChatResult(answer=grounded, used_tools=False, degraded=True)

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
                return ChatResult(answer=answer, used_tools=True, degraded=True)

        return ChatResult(
            answer=answer or GENERIC_ERROR, used_tools=used_tools, degraded=not answer
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
            elif isinstance(m, AIMessage) and m.text:
                turns.append({"role": "assistant", "content": m.text})
        return turns

    def clear(self, session_id: str) -> None:
        self._graph.checkpointer.delete_thread(session_id)


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


def build_agent(repo, mongo_client) -> ChatAgent:
    checkpointer = build_checkpointer(mongo_client)
    return ChatAgent(
        model=build_chat_model(),
        repo=repo,
        checkpointer=checkpointer,
        fallback_models=[build_fallback_model()],
        prune=partial(keep_latest_checkpoint, checkpointer),
    )
