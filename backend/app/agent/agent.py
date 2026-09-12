"""The chatbot agent: a LangGraph tool-calling loop over the database tools."""

import logging
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.mongodb import MongoDBSaver

from app.agent.constants import GENERIC_ERROR, MAX_TOOL_ITERATIONS
from app.agent.llm import build_chat_model
from app.agent.system_prompt import SYSTEM_PROMPT
from app.agent.tools import build_tools
from app.agent.web_fallback import web_answer
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    answer: str
    used_tools: bool
    degraded: bool = False


class ChatAgent:
    def __init__(self, model: BaseChatModel, repo, checkpointer) -> None:
        self._graph = create_agent(
            model=model,
            tools=build_tools(repo),
            system_prompt=SYSTEM_PROMPT,
            checkpointer=checkpointer,
        )

    def _config(self, session_id: str) -> dict:
        return {
            "configurable": {"thread_id": session_id},
            "recursion_limit": MAX_TOOL_ITERATIONS * 2,
        }

    async def answer(self, message: str, session_id: str, allow_web: bool = True) -> ChatResult:
        try:
            state = await self._graph.ainvoke(
                {"messages": [HumanMessage(content=message)]}, config=self._config(session_id)
            )
        except Exception:
            logger.exception("Agent failed for session %s", session_id)
            return ChatResult(answer=GENERIC_ERROR, used_tools=False, degraded=True)

        messages = state["messages"]
        used_tools = any(isinstance(m, ToolMessage) for m in messages)
        answer = messages[-1].content if messages else ""

        # No tool produced data, so the answer is ungrounded. Prefer a labelled web answer
        # over the model's own guess; degraded marks it as not from the app's data.
        if allow_web and not used_tools:
            grounded = await web_answer(message)
            if grounded:
                return ChatResult(answer=grounded, used_tools=False, degraded=True)

        return ChatResult(
            answer=answer or GENERIC_ERROR, used_tools=used_tools, degraded=not answer
        )

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
                turns.append({"role": "user", "content": m.content})
            elif isinstance(m, AIMessage) and m.content:
                turns.append({"role": "assistant", "content": m.content})
        return turns

    def clear(self, session_id: str) -> None:
        self._graph.checkpointer.delete_thread(session_id)


def build_agent(repo, mongo_client) -> ChatAgent:
    checkpointer = MongoDBSaver(
        mongo_client,
        db_name="football_analytics",
        checkpoint_collection_name=settings.checkpoint_collection,
    )
    return ChatAgent(model=build_chat_model(), repo=repo, checkpointer=checkpointer)
