"""Flag figures in an answer that no tool row supports. No extra model call."""

import re

_NUMBER = re.compile(r"\d+(?:\.\d+)?")

# Integers this small describe the query ("top 5", "the 3 players"), not a statistic.
_SMALL_COUNT_MAX = 10


def uncited_numbers(answer: str, tool_rows: list[dict]) -> list[str]:
    """Return numeric tokens in the answer that appear in no row. Empty means grounded."""
    values, texts = _row_contents(tool_rows)

    uncited: list[str] = []
    for token in _NUMBER.findall(answer or ""):
        if any(token in text for text in texts):
            continue
        number = float(token)
        if number.is_integer() and number <= _SMALL_COUNT_MAX:
            continue
        if any(_is_rendering_of(token, number, value) for value in values):
            continue
        uncited.append(token)
    return uncited


def _row_contents(tool_rows: list[dict]) -> tuple[list[float], list[str]]:
    values: list[float] = []
    texts: list[str] = []
    for row in tool_rows or []:
        for value in (row or {}).values():
            if isinstance(value, bool):
                continue
            if isinstance(value, int | float):
                values.append(float(value))
            elif isinstance(value, str):
                texts.append(value)
    return values, texts


def _is_rendering_of(token: str, number: float, value: float) -> bool:
    """True when the token could be `value` written to the token's own precision."""
    decimals = len(token.split(".")[1]) if "." in token else 0
    tolerance = 0.5 * (10**-decimals)
    return abs(value - number) <= tolerance
