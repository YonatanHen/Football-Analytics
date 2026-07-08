import os
from pathlib import Path

CATALOG_DB_PATH = Path(__file__).resolve().parent / "data" / "catalog.sqlite3"
BACKEND_URL = os.environ.get("FETCH_CLI_BACKEND_URL", "http://localhost:8000")

# comps.yaml only tags a couple of women's competitions with a Sofascore id;
# "women" doesn't appear in "WSL" so those two need an explicit name. App is
# men's football only.
WOMENS_EXCLUDE = {"England WSL", "England WSL 2"}
