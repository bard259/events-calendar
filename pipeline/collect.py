"""Orchestrator: run every collector, store events, record the run + per-collector reports.
Then runs stock-impact analysis on all collected events and persists impacts to DB.
"""
from __future__ import annotations

import argparse
import calendar as _calendar

import config
import db
from collectors import ALL_COLLECTORS
from analysis.stock_impact import analyze_all


def run(month: str) -> None:
    month_start = f"{month}-01"
    year, mon = (int(x) for x in month.split("-"))
    last = _calendar.monthrange(year, mon)[1]
    month_end = f"{month}-{last:02d}"

    conn = db.connect()
    db.init_db(conn)

    bytes_before = db.db_size_bytes()
    run_id = db.start_run(conn, month, bytes_before)

    print(f"Collecting events for {month} ({month_start} … {month_end})\n")
    grand_total_new = 0
    grand_total_seen = 0

    for Collector in ALL_COLLECTORS:
        c = Collector(month_start, month_end)
        events, report = c.run()
        new = db.upsert_events(conn, events)
        report.events_collected = len(events)
        db.save_report(conn, run_id, report)
        grand_total_new += new
        grand_total_seen += len(events)

        flags = []
        if report.rate_limited:
            flags.append("RATE-LIMITED")
        if report.tos_issues:
            flags.append(f"{len(report.tos_issues)} ToS")
        if report.errors:
            flags.append(f"{len(report.errors)} err")
        flag_str = ("  [" + ", ".join(flags) + "]") if flags else ""
        print(f"  [{report.status:7}] cat {report.category_id} "
              f"{report.collector:26} {len(events):4} events "
              f"({new} new, {report.http_requests} reqs){flag_str}")

    # ── Stock impact analysis ──────────────────────────────────────────────
    print("\nRunning stock impact analysis…")
    all_events = [dict(r) for r in conn.execute(
        "SELECT uid, category_id, title, description, entity FROM events")]
    impacts = analyze_all(all_events)
    db.save_stock_impacts(conn, impacts)
    print(f"  {len(impacts)} stock-impact records written.")

    # ── Pre-event setup signals (short interest / activist / asymmetry) ────────
    from analysis import setup_signals, earnings_preview
    n_setups = setup_signals.enrich_and_save(conn)
    print(f"  {n_setups} pre-event setup records written.")
    n_prev = earnings_preview.enrich_and_save(conn)
    print(f"  {n_prev} earnings-preview annotations written.")

    total_events = conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
    bytes_after = db.db_size_bytes()
    db.finish_run(conn, run_id, total_events, grand_total_new, bytes_after)
    conn.close()

    print(f"\nDone. {grand_total_seen} events seen this run, {grand_total_new} new, "
          f"{total_events} total in DB.")
    print(f"DB file: {config.DB_PATH}  ({bytes_after:,} bytes)")
    print("Run `python3 pipeline/report.py` for the full storage + issues report.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Collect June-2026 events into SQLite.")
    ap.add_argument("--month", default=config.TARGET_MONTH, help="YYYY-MM (default 2026-06)")
    args = ap.parse_args()
    run(args.month)
