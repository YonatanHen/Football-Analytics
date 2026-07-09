import argparse
import re
import sys
import time

import requests

from .backend_client import BackendClient
from .catalog_repository import CatalogRepository, SeasonInfo
from .config import BACKEND_URL, CATALOG_DB_PATH

_TERMINAL_JOB_STATES = {"done", "partial", "error"}
_CLUB_SEASON_LABEL = re.compile(r"^(\d{2})/(\d{2})$")


def _expand_year(two_digit: str) -> int:
    year = int(two_digit)
    return (2000 if year <= 30 else 1900) + year


def _to_app_season(season_label: str) -> str:
    """Map a Sofascore season label to the app's storage-key season identifier.

    Club leagues use "YY/YY" (e.g. "25/26") -> "YYYY-YYYY" ("2025-2026"), matching the
    app's existing convention so data lands under the same season key the rest of the
    app (players list, etc.) already queries by. Single-year tournaments (e.g. "2026")
    pass through unchanged — there's no two-year form to expand, and
    SofascoreClient._season_to_sofascore_year() already passes those straight through.

    Only the start year is century-expanded; the end year is always start + 1 (a club
    season never spans more than one calendar-year boundary), so a label straddling the
    century-cutoff heuristic (e.g. "30/31") can't produce a decreasing/inconsistent range.
    """
    m = _CLUB_SEASON_LABEL.match(season_label)
    if not m:
        return season_label
    start, _end = m.groups()
    start_year = _expand_year(start)
    return f"{start_year}-{start_year + 1}"


def _top_n_seasons(valid: dict[str, int], n: int) -> list[tuple[str, int]]:
    """Return the n most recent seasons (highest season_id = most recent) as (label, id) pairs."""
    return sorted(valid.items(), key=lambda kv: kv[1], reverse=True)[:n]


def _current_task_label(status: dict) -> str:
    """Describe what's actually running right now.

    Fetch tasks run concurrently (one per position group), so job.current — a single
    field updated only when a task *starts* — freezes on whichever task started last
    once all workers have picked up their tasks. List every task still "running"
    instead, which reflects the real in-flight state.
    """
    running = [t["label"] for t in status.get("tasks", []) if t.get("status") == "running"]
    return ", ".join(running) if running else status["current"] or status["status"]


def _cmd_refresh(args: argparse.Namespace) -> None:
    client = BackendClient(args.backend_url)

    try:
        names = client.list_competitions()
    except requests.RequestException as exc:
        print(f"Could not reach backend at {args.backend_url}: {exc}")
        return

    if args.only:
        names = [n for n in names if n == args.only]
        if not names:
            print(f"Unknown competition: {args.only}")
            return

    seasons: list[SeasonInfo] = []
    failed: list[str] = []
    for name in names:
        try:
            valid = client.get_seasons(name)
        except requests.RequestException as exc:
            print(f"  ! failed to fetch seasons for {name}: {exc}")
            failed.append(name)
            continue
        top = _top_n_seasons(valid, args.seasons)
        seasons.extend(
            SeasonInfo(competition=name, season_label=label, season_id=season_id)
            for label, season_id in top
        )
        print(f"  {name}: {len(top)} seasons")

    if args.only and failed:
        print(f"\nFailed to refresh {args.only!r} — catalog left unchanged.")
        return

    repo = CatalogRepository(CATALOG_DB_PATH)
    try:
        if args.only:
            repo.upsert_competition(names[0], seasons)
        else:
            repo.replace_all(names, seasons)
    finally:
        repo.close()

    print(f"\nRefreshed catalog: {len(names)} competitions, {len(seasons)} seasons.")
    print(f"Written to {CATALOG_DB_PATH}")


def _cmd_browse(args: argparse.Namespace) -> None:
    repo = CatalogRepository(CATALOG_DB_PATH)
    try:
        if repo.is_empty():
            print("Catalog is empty - run `refresh` first.")
            return

        if args.competition:
            seasons = repo.list_seasons(args.competition)
            if not seasons:
                print(f"No seasons found for '{args.competition}'.")
                return
            for s in seasons:
                print(f"  {s.season_label}  (season_id={s.season_id})")
        else:
            for name in repo.list_competitions():
                print(name)
            print(f"\nLast refreshed: {repo.last_refreshed_at()}")
    finally:
        repo.close()


def _prompt_choice(label: str, items: list[tuple[str, str]]) -> str | None:
    """Show a numbered menu of (display, value) pairs; return the chosen value or None."""
    print(f"\n{label}")
    for i, (display, _value) in enumerate(items, 1):
        print(f"  {i}. {display}")
    raw = input("Select a number (blank to cancel): ").strip()
    if not raw:
        return None
    try:
        idx = int(raw)
    except ValueError:
        print("Not a number.")
        return None
    if not (1 <= idx <= len(items)):
        print("Out of range.")
        return None
    return items[idx - 1][1]


def _cmd_fetch(args: argparse.Namespace) -> None:
    client = BackendClient(args.backend_url)

    repo = CatalogRepository(CATALOG_DB_PATH)
    try:
        if repo.is_empty():
            print("Catalog is empty - run `refresh` first.")
            return
        competitions = repo.list_competitions()

        try:
            fetched = client.get_fetched_leagues()
        except requests.RequestException as exc:
            print(f"Could not reach backend at {args.backend_url}: {exc}")
            return
        fetched_by_comp: dict[str, list[str]] = {}
        for f in fetched:
            fetched_by_comp.setdefault(f["competition"], []).append(f["season"])

        comp_items = [
            (
                f"{name}  [fetched: {', '.join(sorted(fetched_by_comp[name]))}]"
                if name in fetched_by_comp
                else name,
                name,
            )
            for name in competitions
        ]
        competition = _prompt_choice("Competitions:", comp_items)
        if competition is None:
            print("Cancelled.")
            return

        seasons = repo.list_seasons(competition)
        if not seasons:
            print(f"No seasons cataloged for '{competition}' - try `refresh`.")
            return

        already_fetched = set(fetched_by_comp.get(competition, []))
        season_items = [
            (
                f"{s.season_label}  [already fetched]"
                if _to_app_season(s.season_label) in already_fetched
                else s.season_label,
                s.season_label,
            )
            for s in seasons
        ]
        season_label = _prompt_choice(f"Seasons for {competition}:", season_items)
        if season_label is None:
            print("Cancelled.")
            return
    finally:
        repo.close()

    app_season = _to_app_season(season_label)
    if app_season in already_fetched:
        confirm = (
            input(f"\n{competition} / {season_label} was already fetched. Fetch again? [y/N]: ")
            .strip()
            .lower()
        )
        if confirm != "y":
            print("Cancelled.")
            return

    print(f"\nTriggering fetch: {competition} / {season_label} ...")
    try:
        job = client.trigger_fetch(app_season, competition)
    except requests.RequestException as exc:
        print(f"Failed to start fetch: {exc}")
        return

    job_id = job["job_id"]
    status: dict = {}
    while True:
        time.sleep(2)
        try:
            status = client.get_fetch_job_status(job_id)
        except requests.RequestException as exc:
            print(f"Failed to poll fetch status: {exc}")
            return
        current = _current_task_label(status)
        print(f"  {status['completed']}/{status['total']} tasks - {current}")
        if status["status"] in _TERMINAL_JOB_STATES:
            break

    print(
        f"\nFetch {status['status']}: {status['players_upserted']} players upserted, "
        f"{status['competitions_failed']} competitions failed."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fetch-cli", description="Sofascore competition catalog tool"
    )
    parser.add_argument(
        "--backend-url", default=BACKEND_URL, help=f"backend base URL (default: {BACKEND_URL})"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_refresh = sub.add_parser("refresh", help="repopulate the catalog from the backend")
    p_refresh.add_argument(
        "--only", help="only refresh this one competition (exact name), for quick testing"
    )
    p_refresh.add_argument(
        "--seasons",
        type=int,
        default=5,
        help="keep only the N most recent seasons per competition (default: 5)",
    )
    p_refresh.set_defaults(func=_cmd_refresh)

    p_browse = sub.add_parser("browse", help="list competitions, or seasons for one competition")
    p_browse.add_argument(
        "competition", nargs="?", default=None, help="competition name to list seasons for"
    )
    p_browse.set_defaults(func=_cmd_browse)

    p_fetch = sub.add_parser(
        "fetch", help="interactively pick a competition + season and load it into MongoDB"
    )
    p_fetch.set_defaults(func=_cmd_fetch)

    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
