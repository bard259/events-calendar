"""Daily incremental update — pull the latest REAL events and merge them in.

Run this once a day (cron / launchd / Claude /schedule). It:
  1. Re-mines the live sources that surface fresh, dated events across the whole window:
       • DailyTechNewsCollector — Google News RSS, marquee tech catalysts (real, dated)
       • OperationalCollector   — Launch Library 2 API, real rocket launches
  2. Upserts into events.db (INSERT OR IGNORE → only genuinely new events are added).
  3. Generates stock impacts for the NEW events only (existing rows are untouched).
  4. Re-exports app/assets/events.json so the calendar app picks up the additions.

Idempotent: running it repeatedly on the same day adds nothing new. As news breaks and
launch schedules firm up, subsequent days surface more confirmed events automatically.

Usage:
    python3 pipeline/daily_update.py                  # window = config range
    python3 pipeline/daily_update.py --start 2026-06-01 --end 2026-12-31
"""
from __future__ import annotations

import argparse

import db
import export_for_app
from analysis.stock_impact import analyze_all
from collectors.daily_news import DailyTechNewsCollector
from collectors.official_events import OfficialEventsCollector
from collectors.operational import OperationalCollector

# Collectors that meaningfully yield fresh, dated events on a daily cadence.
DAILY_COLLECTORS = [
    (DailyTechNewsCollector, {}),
    (OfficialEventsCollector, {}),           # official-site flagship conference dates
    (OperationalCollector, {"LIMIT": 120}),  # widen for the multi-month window
]


def run(start: str, end: str) -> None:
    conn = db.connect()
    db.init_db(conn)

    existing = {row["uid"] for row in conn.execute("SELECT uid FROM events")}
    print(f"Daily update — window {start} … {end}\n(DB has {len(existing)} events)\n")

    all_new: list = []
    for Collector, attrs in DAILY_COLLECTORS:
        c = Collector(start, end)
        for k, v in attrs.items():
            setattr(c, k, v)
        events, report = c.run()
        new_events = [e for e in events if e.uid not in existing]
        db.upsert_events(conn, events)
        for e in new_events:
            existing.add(e.uid)
        all_new.extend(new_events)
        flags = []
        if report.rate_limited:
            flags.append("RATE-LIMITED")
        if report.tos_issues:
            flags.append(f"{len(report.tos_issues)} ToS")
        flag_str = ("  [" + ", ".join(flags) + "]") if flags else ""
        print(f"  {c.source:20} {len(events):4} seen, {len(new_events):3} NEW"
              f"  ({report.http_requests} reqs){flag_str}")

    # Stock impacts for the new events only (idempotent: clear then insert for these uids)
    if all_new:
        uids = [e.uid for e in all_new]
        conn.executemany("DELETE FROM event_stock_impacts WHERE event_uid=?", [(u,) for u in uids])
        conn.commit()
        rows = [{"uid": e.uid, "category_id": e.category_id, "title": e.title,
                 "description": e.description, "entity": e.entity} for e in all_new]
        impacts = analyze_all(rows)
        db.save_stock_impacts(conn, impacts)
        print(f"\n  {len(impacts)} stock-impact records written for {len(all_new)} new events")

        print("\n  New events:")
        for e in sorted(all_new, key=lambda x: x.event_date):
            print(f"    {e.event_date} [cat{e.category_id}] {e.entity or '—':12} {e.title[:60]}")
    else:
        print("\n  No new events today.")

    # Recompute pre-event setup signals across all events (cheap, no network).
    from analysis import setup_signals, earnings_preview
    n_setups = setup_signals.enrich_and_save(conn)
    print(f"  {n_setups} pre-event setup records (short interest / activist / asymmetry)")
    n_prev = earnings_preview.enrich_and_save(conn)
    print(f"  {n_prev} earnings-preview annotations")

    total = conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
    conn.close()
    print(f"\n  Total events in DB: {total}")

    export_for_app.main()


if __name__ == "__main__":
    import config
    ap = argparse.ArgumentParser(description="Daily incremental real-event update.")
    ap.add_argument("--start", default=config.RANGE_START)
    ap.add_argument("--end", default=config.RANGE_END)
    args = ap.parse_args()
    run(args.start, args.end)
