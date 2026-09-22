from unittest.mock import MagicMock

from app.agent.tools import FAMILIES, build_tools
from app.domain.metric_fields import METRIC_FIELDS

METRIC_FAMILIES = [f for f in FAMILIES if f.__name__.rsplit(".", 1)[-1] != "identity"]


def test_every_allowlisted_metric_belongs_to_exactly_one_family():
    seen: list[str] = []
    for family in METRIC_FAMILIES:
        seen.extend(family.functions.METRICS)
    assert len(seen) == len(set(seen)), "a metric appears in two families"
    assert set(seen) == set(METRIC_FIELDS), "families must cover METRIC_FIELDS exactly"


def test_each_family_declares_a_description():
    # The description is the only routing text sent; it must say what the tool covers
    # and when to prefer it, because the system prompt no longer repeats that.
    for family in FAMILIES:
        assert family.prompts.DESCRIPTION.strip()
        assert not hasattr(family.prompts, "GUIDANCE"), (
            f"{family.__name__} still declares GUIDANCE; it would be sent twice per turn"
        )


def test_build_tools_returns_uniquely_named_tools():
    tools = build_tools(MagicMock())
    names = [t.name for t in tools]
    assert len(names) == len(set(names))
    assert "attacking" in names and "goalkeeping" in names
