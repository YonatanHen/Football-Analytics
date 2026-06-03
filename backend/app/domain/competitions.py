import re
import unicodedata

# Maps every known alias (lowercased, stripped) → canonical display name.
# Add entries here as new data sources introduce new spellings.
_ALIASES: dict[str, str] = {
    # England Premier League
    "england premier league": "England Premier League",
    "premier league": "England Premier League",
    "epl": "England Premier League",
    "eng premier league": "England Premier League",
    "english premier league": "England Premier League",
    # Spain La Liga
    "spain la liga": "Spain La Liga",
    "la liga": "Spain La Liga",
    "laliga": "Spain La Liga",
    "es la liga": "Spain La Liga",
    "primera division": "Spain La Liga",
    # Germany Bundesliga
    "germany bundesliga": "Germany Bundesliga",
    "bundesliga": "Germany Bundesliga",
    "de bundesliga": "Germany Bundesliga",
    "1. bundesliga": "Germany Bundesliga",
    # Italy Serie A
    "italy serie a": "Italy Serie A",
    "serie a": "Italy Serie A",
    "it serie a": "Italy Serie A",
    # France Ligue 1
    "france ligue 1": "France Ligue 1",
    "ligue 1": "France Ligue 1",
    "fr ligue 1": "France Ligue 1",
    # UEFA Champions League
    "uefa champions league": "UEFA Champions League",
    "champions league": "UEFA Champions League",
    "ucl": "UEFA Champions League",
    "cl": "UEFA Champions League",
}

# Country-code prefixes that FBref/Kaggle prepend (e.g. "eng Premier League")
_COUNTRY_PREFIX = re.compile(r"^(eng|es|de|it|fr|pt|nl|tr|ru|br|ar|mx|us|au|jp|kr)\s+", re.I)


def _norm(raw: str) -> str:
    text = str(raw).strip().lower()
    text = text.replace("ß", "ss")
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if unicodedata.category(c) != "Mn"
    )
    text = _COUNTRY_PREFIX.sub("", text).strip()
    return text


def canonical_competition(raw: str) -> str:
    """Return the canonical competition display name for any known alias.

    Falls back to title-cased input if the name isn't in the alias table.
    """
    key = _norm(raw)
    if key in _ALIASES:
        return _ALIASES[key]
    # Try without trailing season suffix like " 2025-26"
    key_no_year = re.sub(r"\s+\d{4}[-/]\d{2,4}$", "", key).strip()
    if key_no_year in _ALIASES:
        return _ALIASES[key_no_year]
    return str(raw).strip()
