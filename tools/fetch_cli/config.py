import os
from pathlib import Path

CATALOG_DB_PATH = Path(__file__).resolve().parent / "data" / "catalog.sqlite3"
BACKEND_URL = os.environ.get("FETCH_CLI_BACKEND_URL", "http://localhost:8000")
