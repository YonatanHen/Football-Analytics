import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class SeasonInfo:
    competition: str
    season_label: str
    season_id: int


class CatalogRepository:
    """SQLite-backed catalog of Sofascore competitions and their valid seasons.

    Holds catalog metadata only (competition x season availability) — never player
    stats. Player data continues to flow straight into MongoDB via the existing
    backend fetch pipeline.
    """

    def __init__(self, db_path: str | Path) -> None:
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS competitions (
                name TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS seasons (
                competition TEXT NOT NULL REFERENCES competitions(name) ON DELETE CASCADE,
                season_label TEXT NOT NULL,
                season_id INTEGER NOT NULL,
                PRIMARY KEY (competition, season_label)
            );
            CREATE TABLE IF NOT EXISTS catalog_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def replace_all(self, competitions: list[str], seasons: list[SeasonInfo]) -> None:
        """Atomically replace the full catalog with a freshly fetched snapshot."""
        with self._conn:
            self._conn.execute("DELETE FROM seasons")
            self._conn.execute("DELETE FROM competitions")
            self._conn.executemany(
                "INSERT INTO competitions (name) VALUES (?)",
                [(name,) for name in competitions],
            )
            self._conn.executemany(
                "INSERT INTO seasons (competition, season_label, season_id) VALUES (?, ?, ?)",
                [(s.competition, s.season_label, s.season_id) for s in seasons],
            )
            self._conn.execute(
                "INSERT INTO catalog_meta (key, value) VALUES ('last_refreshed_at', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (datetime.now(UTC).isoformat(),),
            )

    def upsert_competition(self, competition: str, seasons: list[SeasonInfo]) -> None:
        """Replace the seasons for one competition, leaving the rest of the catalog untouched."""
        with self._conn:
            self._conn.execute(
                "INSERT INTO competitions (name) VALUES (?) ON CONFLICT(name) DO NOTHING",
                (competition,),
            )
            self._conn.execute("DELETE FROM seasons WHERE competition = ?", (competition,))
            self._conn.executemany(
                "INSERT INTO seasons (competition, season_label, season_id) VALUES (?, ?, ?)",
                [(s.competition, s.season_label, s.season_id) for s in seasons],
            )
            self._conn.execute(
                "INSERT INTO catalog_meta (key, value) VALUES ('last_refreshed_at', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (datetime.now(UTC).isoformat(),),
            )

    def list_competitions(self) -> list[str]:
        rows = self._conn.execute("SELECT name FROM competitions ORDER BY name").fetchall()
        return [row[0] for row in rows]

    def list_seasons(self, competition: str) -> list[SeasonInfo]:
        rows = self._conn.execute(
            "SELECT competition, season_label, season_id FROM seasons "
            "WHERE competition = ? ORDER BY season_id DESC",
            (competition,),
        ).fetchall()
        return [SeasonInfo(*row) for row in rows]

    def last_refreshed_at(self) -> datetime | None:
        row = self._conn.execute(
            "SELECT value FROM catalog_meta WHERE key = 'last_refreshed_at'"
        ).fetchone()
        return datetime.fromisoformat(row[0]) if row else None

    def is_empty(self) -> bool:
        row = self._conn.execute("SELECT COUNT(*) FROM competitions").fetchone()
        return row[0] == 0
