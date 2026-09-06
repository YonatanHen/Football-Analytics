DESCRIPTION = (
    "Who a player is and what the database holds: look one player up by name, compare "
    "two, or report which competitions and seasons have been fetched."
)

DESCRIPTION_FIND = (
    "Look up one player by name and return their profile: team, position, nationality, "
    "minutes, appearances, goals, assists, s_final and sleeper flag. Returns every "
    "player whose name matches, so use it when a name is ambiguous."
)

DESCRIPTION_COMPARE = (
    "Return one profile row for each of two named players, for side-by-side comparison."
)

DESCRIPTION_COVERAGE = (
    "Report what this database contains: which club and national competitions have been "
    "fetched, and for which seasons. Use it when asked what data is available."
)

GUIDANCE = (
    "identity — find_player looks a player up by name, compare_players returns a row for "
    "each of two players, data_coverage says which competitions and seasons the database "
    "holds. The metric tools already accept player_name, so do NOT call find_player first "
    "just to resolve a name; call it only when a name is ambiguous, when you need a full "
    "profile, or when the user asks who someone is. An empty result means no player "
    "matched — never invent one."
)
