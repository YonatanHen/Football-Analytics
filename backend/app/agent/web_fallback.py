"""Last-resort web-grounded answer. Used only when no tool produced data.

Stays on the LangChain path: langchain-google-genai accepts {"google_search": {}} as a
special tool dict and converts it to types.Tool(google_search=...), so no provider SDK is
called here.
"""

import logging

logger = logging.getLogger(__name__)

_GROUNDING_TOOL = {"google_search": {}}

WEB_LABEL = "Not from the app's data — from a web search:"


async def web_answer(question: str) -> str | None:
    """Return a labelled grounded answer, or None if grounding is unavailable or fails."""
    try:
        from app.agent.llm import build_chat_model

        model = build_chat_model().bind_tools([_GROUNDING_TOOL])
        result = await model.ainvoke(question)
        text = (result.content or "").strip()
        return f"{WEB_LABEL} {text}" if text else None
    except Exception:
        logger.exception("Web fallback failed")
        return None
