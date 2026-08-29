"""Scrape US-company earnings call dates from Yahoo Finance's earnings calendar.

Yahoo's calendar page is a JS/consent shell; the data loads from the authenticated
`query{1,2}.finance.yahoo.com/v1/finance/visualization` endpoint, which needs a cookie +
crumb. This module does that handshake (with retry/backoff), pages a date window, and
integrates each row as a category-3 earnings Event (source="yahoo_earnings_calendar"),
de-duplicated against any earnings already in the DB for the same ticker+date.

NOTE: Yahoo aggressively rate-limits / blocks datacenter IPs (HTTP 429/406). When that
happens this records a ToS/rate-limit note and exits cleanly without inventing data — the
project's reachable equivalent is `scrape_earnings_previews.py` (Nasdaq calendar). Run this
from an environment Yahoo will serve.

    python3 pipeline/scrape_yahoo_earnings.py --start 2026-06-01 --end 2026-12-31
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

import db
import export_for_app
from analysis.stock_impact import analyze_all
from models import Event

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0 Safari/537.36")
VIZ = "https://query2.finance.yahoo.com/v1/finance/visualization"


def _session():
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA), ("Accept", "application/json,text/html")]
    return op


def _crumb(op) -> str | None:
    for attempt in range(4):
        try:
            op.open(urllib.request.Request("https://finance.yahoo.com/quote/AAPL",
                                           headers={"User-Agent": UA}), timeout=20)
            c = op.open(urllib.request.Request("https://query2.finance.yahoo.com/v1/test/getcrumb",
                                               headers={"User-Agent": UA}), timeout=20).read().decode()
            if c and "<" not in c and "Too Many" not in c:
                return c
        except Exception:
            pass
        time.sleep(2 * (attempt + 1))
    return None


def _query_day(op, crumb, day: str, size=250) -> list[dict] | None:
    nxt = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
    body = {
        "sortType": "ASC", "entityIdType": "earnings", "sortField": "ticker",
        "includeFields": ["ticker", "companyshortname", "startdatetime", "startdatetimetype", "epsestimate"],
        "query": {"operator": "and", "operands": [
            {"operator": "gte", "operands": ["startdatetime", day]},
            {"operator": "lt", "operands": ["startdatetime", nxt]},
            {"operator": "eq", "operands": ["region", "us"]}]},
        "offset": 0, "size": size,
    }
    url = f"{VIZ}?crumb={urllib.parse.quote(crumb)}"
    try:
        r = op.open(urllib.request.Request(url, data=json.dumps(body).encode(),
                    headers={"User-Agent": UA, "Content-Type": "application/json"}), timeout=25)
        doc = (((json.load(r).get("finance") or {}).get("result") or [{}])[0].get("documents") or [{}])[0]
        cols = [c.get("id") for c in (doc.get("columns") or [])]
        return [dict(zip(cols, row)) for row in (doc.get("rows") or [])]
    except urllib.error.HTTPError as e:
        return None if e.code in (401, 429, 406, 403) else []
    except Exception:
        return []


def _event(day: str, row: dict, scraped_at: str) -> Event | None:
    ticker = str(row.get("ticker") or "").strip().upper()
    name = str(row.get("companyshortname") or "").strip()
    if not ticker or not name:
        return None
    when = {"BMO": "before the open", "AMC": "after the close", "TAS": "time not supplied"}.get(
        str(row.get("startdatetimetype") or "").upper(), "")
    eps = row.get("epsestimate")
    return Event(
        category_id=3, title=f"{name}: earnings / results",
        description=(f"Earnings report from the Yahoo Finance earnings calendar. "
                     f"{('Timing: ' + when + '. ') if when else ''}"
                     f"EPS estimate: {eps if eps not in (None, '') else 'not published'}."),
        event_date=day, entity=name, importance="medium",
        source="yahoo_earnings_calendar", source_type="scraper",
        native_id=f"{ticker}:{day}",
        source_url=f"https://finance.yahoo.com/calendar/earnings?day={day}",
        pub_date=scraped_at[:10], pub_source="Yahoo Finance",
        raw={"yahoo_row": row, "ticker": ticker, "scraped_at": scraped_at},
    )


def run(start: str, end: str) -> None:
    conn = db.connect(); db.init_db(conn)
    # existing earnings keyed by (ticker, date) to dedup across sources
    existing = set()
    for r in conn.execute(
        "SELECT i.ticker t, e.event_date d FROM event_stock_impacts i JOIN events e ON e.uid=i.event_uid "
        "WHERE e.category_id=3"):
        existing.add((r["t"], r["d"]))

    op = _session()
    crumb = _crumb(op)
    scraped_at = datetime.now(timezone.utc).isoformat()
    if not crumb:
        print("Yahoo BLOCKED: could not obtain a crumb (datacenter IP rate-limited / 429-406). "
              "No data scraped — use scrape_earnings_previews.py (Nasdaq) as the reachable equivalent.")
        conn.close()
        return

    d, last = date.fromisoformat(start), date.fromisoformat(end)
    events, blocked_days = [], 0
    while d <= last:
        day = d.isoformat()
        rows = _query_day(op, crumb, day)
        if rows is None:
            blocked_days += 1
            time.sleep(3)
            crumb = _crumb(op) or crumb
        else:
            for row in rows:
                ev = _event(day, row, scraped_at)
                if ev and (ev.raw["ticker"], day) not in existing:
                    events.append(ev)
        d += timedelta(days=1)
        time.sleep(0.4)

    new = db.upsert_events(conn, events)
    if events:
        impacts = analyze_all([{"uid": e.uid, "category_id": 3, "title": e.title,
                                "description": e.description, "entity": e.entity,
                                "raw_json": json.dumps(e.raw)} for e in events])
        db.save_stock_impacts(conn, impacts)
        from analysis import setup_signals, earnings_preview, earnings_alpha
        setup_signals.enrich_and_save(conn)
        earnings_preview.enrich_and_save(conn)
        earnings_alpha.enrich_and_save(conn)
    conn.close()
    export_for_app.main()
    print(f"Yahoo earnings scrape {start}→{end}: {len(events)} new earnings rows ({new} inserted); "
          f"{blocked_days} days rate-limited.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scrape Yahoo Finance earnings calendar → cat-3 events.")
    ap.add_argument("--start", default="2026-06-01")
    ap.add_argument("--end", default="2026-12-31")
    args = ap.parse_args()
    run(args.start, args.end)
