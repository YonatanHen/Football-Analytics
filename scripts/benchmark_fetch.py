"""
Phase 0 benchmark — run INSIDE the backend container:
    docker compose exec backend python /app/../scripts/benchmark_fetch.py

Measures whether position-split concurrent fetching is faster than a single bulk call.
Results determine fetch_concurrency and whether position-split is kept in the app.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ScraperFC import Sofascore  # type: ignore[import]

LEAGUE = "England Premier League"  # smaller than UCL, good for benchmarking
YEAR = "24/25"
POSITIONS = ["Goalkeepers", "Defenders", "Midfielders", "Forwards"]


_MAX_RETRIES = 3
_RETRY_DELAY = 2.0


def _fetch_group(group: str) -> tuple[str, int, float]:
    t0 = time.time()
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            df = Sofascore().scrape_player_league_stats(year=YEAR, league=LEAGUE, selected_positions=[group])
            if df.empty and attempt < _MAX_RETRIES:
                raise ValueError("Empty response")
            elapsed = time.time() - t0
            return group, len(df), elapsed
        except Exception as exc:
            last_exc = exc
            print(f"  [{group}] attempt {attempt}/{_MAX_RETRIES} failed: {exc}")
            if attempt < _MAX_RETRIES:
                time.sleep(_RETRY_DELAY * attempt)
    raise RuntimeError(f"Failed after {_MAX_RETRIES} attempts") from last_exc


def run_baseline() -> tuple[int, float]:
    print("\n=== 1. BASELINE: single scrape_player_league_stats (all positions) ===")
    t0 = time.time()
    df = Sofascore().scrape_player_league_stats(year=YEAR, league=LEAGUE)
    elapsed = time.time() - t0
    print(f"  rows={len(df)}, time={elapsed:.1f}s")
    return len(df), elapsed


def run_serial_split() -> tuple[int, float]:
    print("\n=== 2. SERIAL position-split (4 sequential calls) ===")
    total_rows = 0
    t0 = time.time()
    for group in POSITIONS:
        group_name, rows, t = _fetch_group(group)
        total_rows += rows
        print(f"  {group_name}: rows={rows}, time={t:.1f}s")
    elapsed = time.time() - t0
    print(f"  TOTAL rows={total_rows}, total time={elapsed:.1f}s")
    return total_rows, elapsed


def run_parallel_split(max_workers: int = 4) -> tuple[int, float]:
    print(f"\n=== 3. PARALLEL position-split (ThreadPoolExecutor max_workers={max_workers}) ===")
    total_rows = 0
    t0 = time.time()
    futures = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for group in POSITIONS:
            futures[ex.submit(_fetch_group, group)] = group
        for fut in as_completed(futures):
            try:
                group_name, rows, t = fut.result()
                total_rows += rows
                print(f"  {group_name}: rows={rows}, time={t:.1f}s")
            except Exception as exc:
                print(f"  ERROR: {exc}")
    elapsed = time.time() - t0
    print(f"  TOTAL rows={total_rows}, wall time={elapsed:.1f}s")
    return total_rows, elapsed


if __name__ == "__main__":
    print(f"Benchmarking Sofascore fetch for {LEAGUE} {YEAR}")
    print("=" * 60)

    rows_baseline, t_baseline = run_baseline()
    rows_serial, t_serial = run_serial_split()
    rows_parallel, t_parallel = run_parallel_split(max_workers=4)

    print("\n=== SUMMARY ===")
    print(f"  Baseline (1 call):       {t_baseline:.1f}s  {rows_baseline} rows")
    print(f"  Serial split (4 calls):  {t_serial:.1f}s   {rows_serial} rows")
    print(f"  Parallel split (4 wide): {t_parallel:.1f}s   {rows_parallel} rows")

    speedup = t_baseline / t_parallel if t_parallel > 0 else 0
    print(f"\n  Parallel speedup vs baseline: {speedup:.1f}x")

    if rows_serial == rows_baseline and rows_parallel == rows_baseline:
        print("  Row counts match — position-split is safe (no duplication/gaps).")
    else:
        print(f"  WARNING: row count mismatch! baseline={rows_baseline}, serial={rows_serial}, parallel={rows_parallel}")

    print("\n=== DECISION ===")
    if speedup >= 1.5 and rows_parallel == rows_baseline:
        print("  -> Position-split parallel is worthwhile. Proceed with both-axes plan.")
        print("     Recommended fetch_concurrency=4 (adjust down if memory pressure seen).")
    else:
        print("  -> Position-split doesn't pay off. Use competition-level parallelism only.")
        print("     Set fetch_concurrency based on available memory (~300-500MB per Chromium).")
