"""Offline eval against the live model and DB. Run: AGENT_EVAL=1 pytest tests/agent/eval -v -s"""

import os

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from app.agent.agent import ChatAgent
from app.agent.llm import build_chat_model, build_fallback_model
from app.infrastructure.text_utils import normalize_text

from .cases import CASES, EvalCase

live = pytest.mark.skipif(not os.getenv("AGENT_EVAL"), reason="set AGENT_EVAL=1 to run the eval")


def mentions(answer: str, name: str) -> bool:
    """True when the answer names the player in full or by surname."""
    text, full = normalize_text(answer), normalize_text(name)
    # Surname-only is how people write answers; a shared surname can give a false pass.
    return full in text or full.split()[-1] in text


def grade(case: EvalCase, answer: str, repo) -> tuple[str, str]:
    """Return (verdict, detail); verdict is pass, fail or no-truth."""
    names = case.expected(repo)
    if not names:
        return "no-truth", "the DB has no rows for this question"
    missing = [n for n in names if not mentions(answer, n)]
    return ("fail", f"missing {missing}") if missing else ("pass", "")


@pytest.fixture(scope="module")
def results():
    collected: list[tuple[str, str, str]] = []
    yield collected
    graded = [r for r in collected if r[1] != "no-truth"]
    passed = sum(r[1] == "pass" for r in graded)
    print(f"\n=== eval: {passed}/{len(graded)} passed ({len(collected) - len(graded)} no-truth)")
    for case_id, verdict, detail in collected:
        print(f"  {verdict:8} {case_id} {detail}")


@live
@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.id)
async def test_eval_case(case: EvalCase, live_repo, results):
    agent = ChatAgent(
        model=build_chat_model(),
        repo=live_repo,
        checkpointer=InMemorySaver(),
        fallback_models=[m for m in [build_fallback_model()] if m],
    )
    res = await agent.answer(case.question, session_id=f"eval-{case.id}")
    verdict, detail = grade(case, res.answer, live_repo)
    results.append((case.id, verdict, detail))
    print(f"\n[{case.id}] {res.answer}")
    if verdict == "no-truth":
        pytest.skip(detail)
    assert verdict == "pass", detail
