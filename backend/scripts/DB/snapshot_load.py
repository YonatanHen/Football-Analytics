"""Restore a local JSON snapshot into the dev MongoDB (developer mode).

Replaces player_bios + player_stats + fetch_log with the snapshot contents.
Original _id values are preserved so the bio <-> stats linkage stays intact.
Indexes are re-created automatically by MongoRepository on the next backend
startup. Run from backend/ while the stack is up:

    python scripts/snapshot_load.py cl-2025-2026.json
"""
import os
import sys
from pathlib import Path

from bson import json_util
from pymongo import MongoClient

DB_NAME = "football_analytics"
COLLECTIONS = ["player_bios", "player_stats", "fetch_log"]

SNAPSHOTS_DIR = Path(__file__).resolve().parent.parent / "snapshots"


def _mongo_uri() -> str:
    uri = os.environ.get("MONGO_URI")
    if uri:
        return uri
    return "mongodb://localhost:27017/football_analytics"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: python scripts/snapshot_load.py <snapshot.json>")

    infile = sys.argv[1]
    in_path = Path(infile)
    if not in_path.is_absolute() and not in_path.exists():
        in_path = SNAPSHOTS_DIR / infile
    if not in_path.exists():
        sys.exit(f"snapshot not found: {in_path}")

    snapshot = json_util.loads(in_path.read_text(encoding="utf-8"))

    client = MongoClient(_mongo_uri())
    db = client[DB_NAME]
    if db.name != DB_NAME:  # guard against an unexpected URI default db
        sys.exit(f"refusing to load into db '{db.name}', expected '{DB_NAME}'")

    print(f"Replacing collections in '{DB_NAME}' from {in_path} ...")
    for coll in COLLECTIONS:
        docs = snapshot.get(coll, [])
        db[coll].drop()
        if docs:
            db[coll].insert_many(docs)
        print(f"  {coll}: {len(docs)} docs loaded")

    print("Done. Restart/refresh the backend to rebuild indexes if needed.")


if __name__ == "__main__":
    main()
