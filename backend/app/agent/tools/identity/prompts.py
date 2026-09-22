DESCRIPTION = (
    "Who a player is and what the database holds: look one player up by name, compare "
    "two, or report which competitions and seasons have been fetched."
)

DESCRIPTION_FIND = (
    "Look up one player by name: team, position, nationality, minutes, appearances, "
    "goals, assists, s_final and sleeper flag. The metric tools already accept "
    "player_name, so do NOT call this just to resolve a name — call it only when a name "
    "is ambiguous, you need a full profile, or the user asks who someone is. An empty "
    "result means no player matched; never invent one."
)

DESCRIPTION_COMPARE = (
    "Return one profile row for each of two named players, for side-by-side comparison."
)

DESCRIPTION_COVERAGE = (
    "Report what this database contains: which club and national competitions have been "
    "fetched, and for which seasons. Use it when asked what data is available."
)
