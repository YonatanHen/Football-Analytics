"""Dump the dev MongoDB to a local JSON snapshot (developer mode).

Exports player_bios + player_stats + fetch_log as MongoDB Extended JSON so the
ObjectId _id <-> player_bio_id linkage is preserved exactly. Run from backend/
while the stack is up (Mongo is exposed on localhost:27017):

    python scripts/snapshot_dump.py                 # -> snapshots/cl-2025-2026.json
    python scripts/snapshot_dump.py my-snapshot.json
"""

import os
import sys
from pathlib import Path

from bson import json_util
from pymongo import MongoClient

DB_NAME = "football_analytics"
COLLECTIONS = ["player_bios", "player_stats", "fetch_log"]
DEFAULT_OUTFILE = "cl-2025-2026.json"

SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent / "snapshots"


def _mongo_uri() -> str:
    uri = os.environ.get("MONGO_URI")
    if uri:
        return uri
    # Fall back to app config default (localhost:27017) without importing the app.
    return "mongodb://localhost:27017/football_analytics"


def main() -> None:
    outfile = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTFILE
    SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SNAPSHOTS_DIR / outfile

    client = MongoClient(_mongo_uri())
    db = client[DB_NAME]

    snapshot: dict[str, list] = {}
    for coll in COLLECTIONS:
        docs = list(db[coll].find({}))
        snapshot[coll] = docs
        print(f"  {coll}: {len(docs)} docs")

    out_path.write_text(json_util.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"Wrote snapshot -> {out_path}")


if __name__ == "__main__":
    main()
