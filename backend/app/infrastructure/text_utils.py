import unicodedata


def normalize_text(s: object) -> str:
    """Lowercase, strip accents, normalize whitespace. Used for fuzzy player/team matching."""
    text = str(s).lower().strip()
    text = text.replace("ß", "ss")
    return "".join(
        c for c in unicodedata.normalize("NFKD", text)
        if unicodedata.category(c) != "Mn"
    )
