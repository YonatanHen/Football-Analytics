from unittest.mock import MagicMock

from .cases import CASES, EvalCase
from .test_eval import grade, mentions


def test_mentions_accepts_accents_and_surnames():
    assert mentions("Kylian Mbappe leads with 30.", "Kylian Mbappé")
    assert mentions("Saka has 12 assists.", "Bukayo Saka")
    assert not mentions("Saka has 12 assists.", "Martin Odegaard")


def test_grade_fails_when_an_expected_name_is_missing():
    case = EvalCase(id="x", question="q", expected=lambda repo: ["Player A", "Player B"])
    assert grade(case, "Player A is first.", MagicMock()) == ("fail", "missing ['Player B']")
    assert grade(case, "Player A, then Player B.", MagicMock()) == ("pass", "")


def test_grade_reports_no_truth_instead_of_failing():
    case = EvalCase(id="x", question="q", expected=lambda repo: [])
    assert grade(case, "anything", MagicMock())[0] == "no-truth"


def test_case_ids_are_unique():
    ids = [c.id for c in CASES]
    assert len(ids) == len(set(ids))


def test_truth_is_derived_from_the_repository():
    repo = MagicMock()
    repo.get_players.return_value = ([MagicMock(name="p")], 1)
    repo.get_players.return_value[0][0].name = "Player A"
    for case in CASES:
        if case.id != "outside-data":  # the only case with a fixed, non-repository truth
            assert "Player A" in case.expected(repo)
