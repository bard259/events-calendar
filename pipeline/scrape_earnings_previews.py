"""Scrape June-July earnings reports from nfin/Nasdaq and generate preview rows.

The source is the free nfin wrapper around Nasdaq's public earnings calendar:
https://api.nfin.dev/v1/calendar/earnings?date=YYYY-MM-DD

This script is intentionally calendar-first:
  - scrape one day at a time for an auditable source trail,
  - upsert category-3 earnings events,
  - record every scraped row in earnings_scrape_* tracker tables,
  - refresh stock impacts, setup signals, earnings previews, and the app export.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

import db
import export_for_app
from analysis.stock_impact import analyze_all
from http_client import HttpClient
from models import CollectorReport, Event

SOURCE = "nfin_earnings_calendar"
BASE_URL = "https://api.nfin.dev/v1/calendar/earnings"


def _dates(start: str, end: str):
    d = date.fromisoformat(start)
    last = date.fromisoformat(end)
    while d <= last:
        yield d.isoformat()
        d += timedelta(days=1)


def _clean(value) -> str:
    return str(value or "").strip()


def _time_phrase(value: str) -> str:
    return {
        "time-after-hours": "after the close",
        "time-pre-market": "before the open",
        "time-not-supplied": "time not supplied",
    }.get(value, value.replace("time-", "").replace("-", " ") if value else "time not supplied")


def _event_from_row(day: str, row: dict, scraped_at: str) -> Event | None:
    ticker = _clean(row.get("symbol")).upper()
    company = _clean(row.get("name"))
    if not ticker or not company:
        return None
    eps = _clean(row.get("epsForecast")) or "not published"
    ests = _clean(row.get("noOfEsts")) or "not supplied"
    fiscal_q = _clean(row.get("fiscalQuarterEnding")) or "not supplied"
    last_year = _clean(row.get("lastYearEPS")) or "not available"
    when = _time_phrase(_clean(row.get("time")))
    return Event(
        category_id=3,
        title=f"{company}: earnings / results",
        description=(
            f"Upcoming earnings report from nfin/Nasdaq calendar. "
            f"Report timing: {when}. EPS target: {eps}. "
            f"Analyst estimates: {ests}. Fiscal quarter: {fiscal_q}. "
            f"Last year's EPS: {last_year}."
        ),
        event_date=day,
        entity=company,
        importance="high" if _is_large_cap(row) else "medium",
        source=SOURCE,
        source_type="api",
        native_id=f"{ticker}:{day}",
        source_url=f"{BASE_URL}?date={quote(day)}",
        pub_date=scraped_at[:10],
        pub_source="nfin/Nasdaq",
        raw={"nfin_row": row, "scraped_at": scraped_at},
    )


def _is_large_cap(row: dict) -> bool:
    cap = _clean(row.get("marketCap")).replace("$", "").replace(",", "")
    try:
        if cap.endswith("T"):
            return float(cap[:-1]) >= 0.2
        if cap.endswith("B"):
            return float(cap[:-1]) >= 200
        return float(cap) >= 200_000_000_000
    except Exception:
        return False


def scrape(start: str, end: str) -> tuple[list[Event], list[dict], CollectorReport, list[str], int]:
    report = CollectorReport(SOURCE, 3, "api")
    http = HttpClient(report, rate_delay=0.15)
    events: list[Event] = []
    tracker_rows: list[dict] = []
    errors: list[str] = []
    days_ok = 0
    scraped_at = datetime.now(timezone.utc).isoformat()

    for day in _dates(start, end):
        url = f"{BASE_URL}?date={quote(day)}"
        payload = http.get_json(url, respect_robots=False)
        if not payload:
            errors.append(f"{day}: no response")
            continue
        table = (((payload.get("data") or {}).get("data") or {}))
        rows = table.get("rows") or []
        days_ok += 1
        for row in rows:
            ev = _event_from_row(day, row, scraped_at)
            if not ev:
                continue
            events.append(ev)
            tracker_rows.append({
                "event_uid": ev.uid,
                "ticker": _clean(row.get("symbol")).upper(),
                "company": _clean(row.get("name")),
                "event_date": day,
                "source": SOURCE,
                "status": "scraped",
                "raw_json": json.dumps(row, ensure_ascii=False),
                "collected_at": scraped_at,
            })

    report.events_collected = len(events)
    report.notes.append(f"Scraped {len(events)} nfin/Nasdaq earnings rows for {start} through {end}.")
    return events, tracker_rows, report, errors, days_ok


def run(start: str, end: str) -> None:
    conn = db.connect()
    db.init_db(conn)

    day_count = sum(1 for _ in _dates(start, end))
    run_id = db.start_earnings_scrape(conn, SOURCE, start, end, day_count)

    existing = {row["uid"] for row in conn.execute("SELECT uid FROM events")}
    events, tracker_rows, report, errors, days_ok = scrape(start, end)
    new_events = [e for e in events if e.uid not in existing]
    inserted = db.upsert_events(conn, events)

    for row in tracker_rows:
        row["run_id"] = run_id
        row["status"] = "new" if row["event_uid"] in {e.uid for e in new_events} else "seen"
    if tracker_rows:
        db.save_earnings_scrape_items(conn, tracker_rows)

    if events:
        uids = [(e.uid,) for e in events]
        conn.executemany("DELETE FROM event_stock_impacts WHERE event_uid=?", uids)
        conn.commit()
        impact_rows = [{
            "uid": e.uid,
            "category_id": e.category_id,
            "title": e.title,
            "description": e.description,
            "entity": e.entity,
            "raw_json": json.dumps(e.raw, ensure_ascii=False),
        } for e in events]
        impacts = analyze_all(impact_rows)
        db.save_stock_impacts(conn, impacts)
    else:
        impacts = []

    from analysis import setup_signals, earnings_preview
    n_setups = setup_signals.enrich_and_save(conn)
    n_previews = earnings_preview.enrich_and_save(conn)

    notes = list(report.notes)
    notes.append("Earnings Labs cross-check: June page says 456 companies; July page says 624 companies.")
    db.finish_earnings_scrape(
        conn, run_id, days_ok=days_ok, rows_seen=len(events), events_inserted=inserted,
        errors=errors + report.errors + report.tos_issues, notes=notes,
    )
    total = conn.execute("SELECT COUNT(*) n FROM events").fetchone()["n"]
    conn.close()
    export_for_app.main()

    print(f"Earnings scrape run #{run_id}: {start} through {end}")
    print(f"  days ok: {days_ok}/{day_count}")
    print(f"  rows scraped: {len(events)}")
    print(f"  new events inserted: {inserted}")
    print(f"  stock-impact records written: {len(impacts)}")
    print(f"  setup records: {n_setups}")
    print(f"  earnings previews: {n_previews}")
    print(f"  total DB events: {total}")
    if errors or report.errors or report.tos_issues:
        print("  issues:")
        for e in errors + report.errors + report.tos_issues:
            print(f"    - {e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scrape June-July earnings reports and refresh previews.")
    ap.add_argument("--start", default="2026-06-02")
    ap.add_argument("--end", default="2026-07-31")
    args = ap.parse_args()
    run(args.start, args.end)
