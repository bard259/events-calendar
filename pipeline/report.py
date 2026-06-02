"""Report: ACTUAL storage footprint + rate-limit / ToS / error summary.

Compares the estimate to the real on-disk size and prints every recorded
rate-limit and Terms-of-Service issue from the latest run.
"""
from __future__ import annotations

import json

import db
from config import CATEGORIES, DB_PATH
from estimate_storage import avg_event_bytes, SQLITE_ROW_OVERHEAD, SQLITE_BASE
from config import EXPECTED_COUNTS


def fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 ** 2:
        return f"{n/1024:,.1f} KiB"
    return f"{n/1024/1024:,.2f} MiB"


def main():
    if not DB_PATH.exists():
        print("No events.db yet — run `python3 pipeline/collect.py` first.")
        return
    conn = db.connect()

    run = conn.execute(
        "SELECT * FROM collection_runs ORDER BY id DESC LIMIT 1").fetchone()
    bd = db.storage_breakdown(conn)

    print("=" * 70)
    print("ACTUAL STORAGE REPORT — events.db")
    print("=" * 70)
    print(f"Latest run:        #{run['id']}  month={run['month']}")
    print(f"Started / finished {run['started_at']}  →  {run['finished_at']}")
    print(f"Total events:      {bd['total_events']}")
    print(f"DB file size:      {fmt_bytes(bd['file_bytes'])}  ({bd['file_bytes']:,} bytes)")
    print(f"Logical payload:   {fmt_bytes(bd['payload_bytes'])}  "
          f"({bd['payload_bytes']:,} bytes of stored text)")
    if bd['total_events']:
        print(f"Avg bytes/event:   file={bd['file_bytes']//bd['total_events']:,}  "
              f"payload={bd['payload_bytes']//bd['total_events']:,}")

    print("-" * 70)
    print(f"{'Cat':>3}  {'Category':38} {'Actual':>8} {'Est.':>6} {'Δ':>6}")
    print("-" * 70)
    for cid, name in CATEGORIES.items():
        actual = bd["counts_by_category"].get(cid, 0)
        est = EXPECTED_COUNTS.get(cid, 0)
        print(f"{cid:>3}  {name:38} {actual:>8} {est:>6} {actual-est:>+6}")
    print("-" * 70)

    # estimate vs actual file size
    per = avg_event_bytes()
    est_bytes = SQLITE_BASE + sum(EXPECTED_COUNTS.values()) * (per + SQLITE_ROW_OVERHEAD)
    print(f"Estimated size (pre-collection): {fmt_bytes(est_bytes)} "
          f"({est_bytes:,} bytes)")
    print(f"Actual size:                     {fmt_bytes(bd['file_bytes'])} "
          f"({bd['file_bytes']:,} bytes)")
    diff = bd['file_bytes'] - est_bytes
    pct = (diff / est_bytes * 100) if est_bytes else 0
    print(f"Difference:                      {diff:+,} bytes ({pct:+.1f}% vs estimate)")

    # --- rate-limit / ToS / error summary --------------------------------
    print("=" * 70)
    print("DATA-SOURCE ISSUES (rate limits / ToS / errors) — latest run")
    print("=" * 70)
    reps = conn.execute(
        "SELECT * FROM collector_reports WHERE run_id=? ORDER BY category_id",
        (run["id"],)).fetchall()
    any_issue = False
    for r in reps:
        tos = json.loads(r["tos_issues"] or "[]")
        errs = json.loads(r["errors"] or "[]")
        notes = json.loads(r["notes"] or "[]")
        header = (f"cat {r['category_id']} · {r['collector']} "
                  f"({r['source_type']}) — {r['status']}, "
                  f"{r['events_collected']} events, {r['http_requests']} HTTP reqs"
                  f"{', RATE-LIMITED' if r['rate_limited'] else ''}")
        print(f"\n• {header}")
        if tos:
            any_issue = True
            for t in tos:
                print(f"    [ToS]   {t}")
        for e in errs:
            any_issue = True
            print(f"    [err]   {e}")
        for n in notes:
            print(f"    note    {n}")
    if not any_issue:
        print("\nNo rate-limit or ToS issues recorded this run. ✅")
    print("=" * 70)
    conn.close()


if __name__ == "__main__":
    main()
