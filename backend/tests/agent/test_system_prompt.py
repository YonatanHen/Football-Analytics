from app.agent.system_prompt import SYSTEM_PROMPT, build_system_prompt
from app.agent.tools import FAMILIES


def test_prompt_does_not_duplicate_tool_descriptions():
    # Tool descriptions are sent with every request as part of the tool schemas.
    # Repeating them here would cost the same tokens twice on every turn.
    for family in FAMILIES:
        assert family.prompts.DESCRIPTION not in SYSTEM_PROMPT


def test_prompt_states_the_scope_and_the_answer_policy():
    lowered = SYSTEM_PROMPT.lower()
    assert "men's" in lowered
    assert "do not invent" in lowered or "never invent" in lowered


def test_prompt_forbids_revealing_reasoning_or_tools():
    lowered = SYSTEM_PROMPT.lower()
    assert "reasoning" in lowered
    assert "tool" in lowered


def test_prompt_sets_a_one_call_default():
    lowered = SYSTEM_PROMPT.lower()
    assert "fewest calls" in lowered
    assert "exactly one" in lowered


def test_prompt_forbids_refusing():
    lowered = SYSTEM_PROMPT.lower()
    assert "do not write a refusal" in lowered


def test_prompt_tells_the_model_not_to_resolve_names_with_identity_first():
    # The main way a one-call question becomes two (spec 7.1).
    lowered = SYSTEM_PROMPT.lower()
    assert "player_name" in lowered
    assert "do not call identity first" in lowered


def test_prompt_requires_flagging_unreliable_rows():
    assert "low_sample_size" in SYSTEM_PROMPT


def test_prompt_stays_small_because_it_is_sent_every_turn():
    rebuilt = build_system_prompt()
    assert rebuilt == SYSTEM_PROMPT
    assert len(SYSTEM_PROMPT) < 2200, "system prompt grew; it is sent on every request"
