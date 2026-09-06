"""Backfill the typed defensive Stats fields from each entry's stored raw_stats.

No re-fetch: the Sofascore defensive columns were always scraped into
competitions[].raw_stats, they were just never promoted into the typed model. Run from
backend/ with Mongo reachable:

    python scripts/DB/backfill_defensive_stats.py            # apply
    python scripts/DB/backfill_defensive_stats.py --dry-run  # report only

Scores are left untouched: ScoringEngine does not read these fields.

Stop any running fetch job first: this rewrites each doc's whole competitions array, so a
concurrent fetch writing between the read and the write would be overwritten.
"""

import os
import sys
from dataclasses import asdict

from pymongo import MongoClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.domain.defensive_stats import DEFENSIVE_RAW_MAP, apply_defensive_raw  # noqa: E402
from app.domain.models import Stats  # noqa: E402

DB_NAME = "football_analytics"


def _mongo_uri() -> str:
    return os.environ.get("MONGO_URI", "mongodb://localhost:27017/football_analytics")


def _stats_from_dict(d: dict) -> Stats:
    valid = set(Stats().__dict__)
    return Stats(**{k: v for k, v in (d or {}).items() if k in valid})


def _aggregate(entries: list[dict]) -> Stats:
    from app.domain.defensive_stats import recompute_rates

    total = Stats()
    for entry in entries:
        s = _stats_from_dict(entry.get("stats"))
        for field in DEFENSIVE_RAW_MAP.values():
            setattr(total, field, getattr(total, field) + getattr(s, field))
    recompute_rates(total)
    return total


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    db = MongoClient(_mongo_uri())[DB_NAME]

    scanned = changed = written = entries_touched = no_raw = 0

    for doc in db.player_stats.find({}):
        scanned += 1
        entries = doc.get("competitions") or []
        updated_entries = []
        doc_changed = False

        for entry in entries:
            stats = _stats_from_dict(entry.get("stats"))
            raw = entry.get("raw_stats") or {}
            if not raw:
                no_raw += 1
            before = asdict(stats)
            apply_defensive_raw(stats, raw)
            if asdict(stats) != before:
                doc_changed = True
                entries_touched += 1
            entry["stats"] = asdict(stats)
            updated_entries.append(entry)

        # Write every doc, not only changed ones. A doc left without the new keys is not
        # merely stale: Mongo's $gte does not match a missing field, so those players
        # disappear from defensive filters, while the stats_view path (which defaults them
        # to 0 in Python) still returns them. Same query, two answers.
        agg = _stats_from_dict(doc.get("aggregated_stats"))
        totals = _aggregate(updated_entries)
        for field in list(DEFENSIVE_RAW_MAP.values()) + [
            "tackles_won_pct",
            "aerial_duels_won_pct",
        ]:
            setattr(agg, field, getattr(totals, field))

        changed += 1 if doc_changed else 0
        if not dry_run:
            written += 1
            db.player_stats.update_one(
                {"_id": doc["_id"]},
                {"$set": {"competitions": updated_entries, "aggregated_stats": asdict(agg)}},
            )

    verb = "would change" if dry_run else "changed"
    print(f"scanned {scanned} player_stats docs")
    print(f"{verb} {changed} docs across {entries_touched} competition entries")
    if dry_run:
        print(f"would write all {scanned} docs (nothing was written: --dry-run)")
    else:
        print(f"wrote {written} docs, so none is left without the new keys")
    print(f"entries with no raw_stats: {no_raw}")


if __name__ == "__main__":
    main()
