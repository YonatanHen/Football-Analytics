"""Eval questions paired with the repository call that computes their true answer."""

from collections.abc import Callable
from dataclasses import dataclass, field

from app.config import settings


@dataclass
class EvalCase:
    id: str
    question: str
    # repo -> player names the answer must mention; None means the answer must be a web answer
    expected: Callable[..., list[str]] | None = field(default=None, repr=False)


def _top(repo, metric: str, n: int, **filters) -> list[str]:
    players, _ = repo.get_players(
        season=settings.season, sort_by=metric, order="desc", page=1, page_size=n, **filters
    )
    return [p.name for p in players]


def _first_match(repo, name: str) -> list[str]:
    players, _ = repo.get_players(season=settings.season, name=name, page=1, page_size=1)
    return [p.name for p in players]


CASES = [
    EvalCase(
        id="top-forwards-goals",
        question="Who are the top 5 forwards by goals?",
        expected=lambda repo: _top(repo, "goals", 5, position="FW"),
    ),
    EvalCase(
        id="gk-clean-sheets",
        question="Which goalkeeper has the most clean sheets?",
        expected=lambda repo: _top(repo, "clean_sheets", 1, position="GK"),
    ),
    EvalCase(
        id="df-tackles",
        question="Which defender has made the most tackles?",
        expected=lambda repo: _top(repo, "tackles", 1, position="DF"),
    ),
    EvalCase(
        id="team-assists",
        question="Who has the most assists at Arsenal?",
        expected=lambda repo: _top(repo, "assists", 1, team="Arsenal"),
    ),
    EvalCase(
        id="nationality-goals",
        question="Which Brazilian player has scored the most goals?",
        expected=lambda repo: _top(repo, "goals", 1, nationality="Brazil"),
    ),
    EvalCase(
        id="compare-two",
        question="Compare Mohamed Salah and Bukayo Saka.",
        expected=lambda repo: _first_match(repo, "Salah") + _first_match(repo, "Saka"),
    ),
    EvalCase(
        id="outside-data",
        question="Which country won the 2018 FIFA World Cup?",
    ),
]
