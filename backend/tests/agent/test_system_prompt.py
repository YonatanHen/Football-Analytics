from datetime import date

from app.agent.system_prompt import build_system_prompt
from app.agent.tools import FAMILIES

TODAY = date(2026, 9, 27)
SYSTEM_PROMPT = build_system_prompt(TODAY)


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
    assert "never refuse" in lowered


def test_prompt_tells_the_model_not_to_resolve_names_with_identity_first():
    # The main way a one-call question becomes two (spec 7.1).
    lowered = SYSTEM_PROMPT.lower()
    assert "player_name" in lowered
    assert "do not call identity first" in lowered


def test_prompt_requires_flagging_unreliable_rows():
    assert "low_sample_size" in SYSTEM_PROMPT


def test_prompt_gives_today_and_the_calendar_seasons():
    # Without the date the model guesses the season from its training data.
    assert "2026-09-27" in SYSTEM_PROMPT
    assert '"this season" means 2026-2027' in SYSTEM_PROMPT.lower()
    assert '"last season" means 2025-2026' in SYSTEM_PROMPT.lower()


def test_prompt_names_the_season_the_database_holds():
    from app.config import settings

    assert f"only the {settings.season} season" in SYSTEM_PROMPT
    assert "still call the tools" in SYSTEM_PROMPT


def test_prompt_separates_leagues_from_combined_totals():
    lowered = SYSTEM_PROMPT.lower()
    assert "each competition separately" in lowered
    assert "combined total" in lowered
    assert "never add other competitions" in lowered


def test_prompt_uses_the_ui_name_for_the_composite_score():
    assert "Fantasy Score" in SYSTEM_PROMPT
    assert "never write s_final" in SYSTEM_PROMPT.lower()
    assert "0-10" in SYSTEM_PROMPT


def test_prompt_follows_the_date():
    assert "2027-03-01" in build_system_prompt(date(2027, 3, 1))


def test_prompt_stays_small_because_it_is_sent_every_turn():
    assert len(SYSTEM_PROMPT) < 3200, "system prompt grew; it is sent on every request"
