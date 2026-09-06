DESCRIPTION = (
    "Team defensive outcomes recorded for a player: clean sheets, goals conceded and "
    "penalties conceded. Rank players, filter by a range, or read one player's value."
)

GUIDANCE = (
    "defending — only clean_sheets, goals_conceded and penalty_conceded can be queried. "
    "Tackles, interceptions and clearances are stored per competition as raw Sofascore "
    "columns, but they are not typed metrics, so no tool can rank or filter on them. If "
    "the user asks for those, return nothing rather than substituting a different metric "
    "— the web fallback will answer and label the source. Never write a refusal yourself."
)
