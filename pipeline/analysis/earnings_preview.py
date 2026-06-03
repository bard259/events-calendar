"""Earnings-preview annotations — qualitative "what to expect" notes for marquee prints.

Like `setup_signals.py`, this is a *sourced, dated* analytical reference layer (NOT event
data): for a handful of high-interest earnings events it attaches the consensus bar, the
options-implied move, a directional lean, and bull/bear/what-to-watch bullets — surfaced in
the app's day-detail as a 📊 EARNINGS PREVIEW block. Each entry carries `as_of` + `sources`
and is research, not advice; refresh before the print (estimates & implied vol move daily).

Keyed by ticker; only attaches to an event that (a) resolves to that ticker via the
stock-impact entity map and (b) is actually an earnings event (keyword-gated), so a
non-earnings headline about the same company won't pick up the preview.
"""
from __future__ import annotations

import json
import re

from analysis.setup_signals import primary_ticker

_EARNINGS_KW = re.compile(r"\b(earnings|results|reports?|quarterly|q[1-4]\b|fiscal)\b", re.I)

# ── Sourced earnings previews (refresh each cycle) ──────────────────────────────
PREVIEWS: dict[str, dict] = {
    "AVGO": {
        "company": "Broadcom",
        "as_of": "2026-06-02 — Q2 FY26, reports Wed 6/3 after close (move shows 6/4)",
        "decision": "Watch closely. Favor a positive reaction only if Broadcom raises its AI outlook; otherwise be cautious after the run-up.",
        "confidence": "Medium-high",
        "significance": "High: this is the biggest AI-chip earnings event on the calendar.",
        "implied_move": "±8–10.6%",
        "avg_move": "±6.7% (last 4 quarters)",
        "lean": "The company is likely to beat expectations, but the stock may only rise if management also raises its AI outlook. After a big run, a merely good report may not be enough.",
        "bar": [
            "Profit target: about $2.40 per share",
            "Sales target: about $22.1B",
            "AI-chip sales need to be clearly above last quarter's $4.1B to impress investors",
        ],
        "watch": [
            "Does management raise the next-quarter AI-chip outlook?",
            "Any new large cloud-customer wins",
            "Whether software profits help offset chip-cost pressure",
        ],
        "bull": "A stronger AI outlook would support the case that Broadcom remains one of the main AI winners.",
        "bear": "The stock is already near highs, so a merely good report could still disappoint investors.",
        "contrast": "Unlike VSXY, expectations are already high here. The bigger surprise risk is disappointment.",
        "sources": [
            "https://news.alphastreet.com/broadcom-avgo-q2-2026-preview-eps-est-2-40-reports-june-3/amp/",
            "https://www.tipranks.com/news/broadcom-is-about-to-report-q2-earnings-options-traders-expect-a-10-65-move-in-avgo-stock",
            "https://www.heygotrade.com/en/blog/broadcom-avgo-q2-fy26-earnings-preview/",
            "https://www.marketbeat.com/stocks/NASDAQ/AVGO/forecast/",
        ],
    },
    "VSXY": {
        "company": "Victoria's Secret",
        "as_of": "Q1 FY26 — REPORTED 2026-06-02",
        "decision": "Result was strongly positive. Mark this as a completed high-conviction upside event.",
        "confidence": "High",
        "significance": "High: the report changed the turnaround story and drove a very large move.",
        "implied_move": "realized ~+50%",
        "avg_move": "",
        "lean": "Reported 6/2 with a much stronger result than expected. Profit, sales, and full-year guidance all improved, and the stock jumped about 50%.",
        "bar": [
            "Profit was far above expectations",
            "Sales grew 15% from last year",
            "Management raised the full-year outlook",
        ],
        "watch": ["Do sales keep improving?", "Do profits keep expanding?", "Do activist investors push for more changes?"],
        "bull": "The turnaround looks real after several improving quarters.",
        "bear": "After the big move, the next report will need to be strong too.",
        "sources": [
            "https://www.stocktitan.net/news/VSCO/victoria-s-secret-co-reports-first-quarter-2026-73nczgypqqis.html",
            "https://www.investing.com/news/earnings/victorias-secret-shares-gain-on-earnings-beat-guidance-raise-4721575",
        ],
    },
    "CTRN": {
        "company": "Citi Trends",
        "as_of": "Q1 FY26 — REPORTED 2026-06-02",
        "decision": "Result was positive. Keep on watch, but treat the move as smaller and less certain than VSXY.",
        "confidence": "Medium",
        "significance": "Medium: small company, strong report, but less market-wide importance.",
        "implied_move": "shares surged",
        "avg_move": "",
        "lean": "Reported 6/2 with better profit and sales than expected. Store sales stayed strong and the company raised its full-year outlook.",
        "bar": [
            "Profit was a little better than expected",
            "Sales grew more than 14%",
            "Management raised the full-year outlook",
        ],
        "watch": ["Can store sales stay strong?", "Are shoppers responding to the merchandise?", "Can profit margins hold up?"],
        "bull": "The turnaround is gaining momentum.",
        "bear": "Small stock with thinner trading, so moves can reverse quickly.",
        "sources": [
            "https://www.stocktitan.net/sec-filings/CTRN/8-k-citi-trends-inc-reports-material-event-71a278913b58.html",
            "https://www.fool.com/earnings/call-transcripts/2026/06/02/citi-trends-ctrn-q1-2026-earnings-transcript/",
        ],
    },
    "CAL": {
        "company": "Caleres",
        "as_of": "Q1 FY26 — reports 2026-06-04 pre-market (UPCOMING)",
        "decision": "Neutral to slightly positive. Watch the report, but do not force a strong call unless guidance improves.",
        "confidence": "Medium",
        "significance": "Medium: useful consumer-demand read, but not a broad market mover.",
        "implied_move": "n/a (thin options)",
        "avg_move": "",
        "lean": "Reports 6/4 before the open. The company's own target is slightly above Wall Street's estimate, so the key question is whether demand and full-year guidance hold up.",
        "bar": [
            "Profit target: about $0.34 per share",
            "Sales target: about $662.6M",
            "The company's own outlook is slightly better than Wall Street's target",
        ],
        "watch": ["Famous Footwear store traffic", "Wholesale demand", "Tariff and sourcing costs", "Full-year outlook"],
        "bull": "Demand may be steadier than investors expect.",
        "bear": "Footwear spending is sensitive to weaker consumers and higher import costs.",
        "sources": [
            "https://www.tradingview.com/news/tradingview:39fe85bb04cda:0-cal-q1-26-earnings-revenue-estimate-is-662-64m-usd/",
            "https://www.sec.gov/Archives/edgar/data/0000014707/000001470726000062/cal-20260520xex99d1.htm",
        ],
    },
    "CRON": {
        "company": "Cronos Group",
        "as_of": "scraped 2026-06-20 date is UNVERIFIED; sparse coverage",
        "decision": "Do not rely on this date yet. Verify the event before using it for a trade decision.",
        "confidence": "Low",
        "significance": "Low-medium: interesting stock-specific story, but the date is uncertain.",
        "implied_move": "n/a",
        "avg_move": "",
        "lean": "Coverage is thin and the scraped 6/20 earnings date is uncertain. The main things to confirm are sales growth and the path to profitability.",
        "bar": [
            "Limited published consensus (4 analysts)",
            "Last quarter's sales were a record $45.2M",
            "Analyst coverage is limited but generally positive",
        ],
        "watch": ["Confirm the actual report date", "Sales growth", "Progress toward profitability", "How cash is used"],
        "bull": "Large net-cash balance; accelerating revenue.",
        "bear": "Cannabis stocks remain volatile, and profitability is still limited.",
        "sources": [
            "https://stockanalysis.com/stocks/cron/",
            "https://www.nasdaq.com/market-activity/stocks/cron/earnings",
        ],
    },
    "PLUS": {
        "company": "ePlus",
        "as_of": "Q4 FY26 — REPORTED 2026-05-28 (scraped 6/30 date is INCORRECT)",
        "decision": "Ignore the scraped 6/30 earnings date. The company already reported, and the result was positive.",
        "confidence": "High",
        "significance": "Medium: positive company update, but the calendar date needs correction.",
        "implied_move": "stock rose",
        "avg_move": "",
        "lean": "Data-quality flag: the 6/30 event date appears wrong. ePlus already reported on 5/28, beat expectations, gave a strong outlook, and the stock rose.",
        "bar": [
            "Profit was slightly better than expected",
            "Sales grew more than 20%",
            "Management gave a strong next-year outlook",
        ],
        "watch": ["Demand for AI-related services", "Profit mix between products and services", "Follow-through on next-year outlook"],
        "bull": "Services growth and the new outlook were encouraging.",
        "bear": "Hardware demand can be uneven, and analyst coverage is limited.",
        "sources": [
            "https://news.alphastreet.com/eplus-q4-2026-earnings-preview-may-28-street-expects-0-98-eps/",
            "https://www.fool.com/earnings/call-transcripts/2026/05/28/eplus-plus-q4-2026-earnings-transcript/",
        ],
    },
    "GEF": {
        "company": "Greif",
        "as_of": "Q2 FY26 — REPORTED ~2026-06-02 (scraped 6/30 date is INCORRECT)",
        "decision": "Ignore the scraped 6/30 earnings date. The company already reported, and the result was weak.",
        "confidence": "High",
        "significance": "Medium: company-specific negative result and another calendar-quality warning.",
        "implied_move": "",
        "avg_move": "",
        "lean": "Data-quality flag: the 6/30 event date appears wrong. Greif already reported, missed expectations, and reduced its full-year outlook. Better margins were the main offset.",
        "bar": [
            "Sales came in below expectations",
            "Profit also missed expectations",
            "Management lowered the full-year profit outlook",
        ],
        "watch": ["Packaging demand", "Pricing versus costs", "Cash generation", "Impact from sold or closed business lines"],
        "bull": "Margins and cash generation showed some improvement.",
        "bear": "Demand is soft, results missed, and the outlook was lowered.",
        "sources": [
            "https://www.tradingview.com/news/tradingview:c654ad952a884:0-greif-q2-2026-revenue-1-072-8m-eps-0-22-operating-profit-down-on-higher-sga/",
            "https://www.fool.com/earnings/call-transcripts/2026/06/02/greif-gef-q2-2026-earnings-call-transcript/",
        ],
    },
}


def build_preview(event: dict) -> dict | None:
    """Return a preview row for an earnings event whose ticker is in PREVIEWS, else None."""
    blob = f"{event.get('title','')} {event.get('description','')} {event.get('entity','')}"
    if not _EARNINGS_KW.search(blob):
        return None
    raw = _load_raw(event.get("raw_json"))
    ticker = _event_ticker(raw) or primary_ticker(blob)
    if not ticker:
        return None
    payload = PREVIEWS.get(ticker) or _build_scraped_preview(event, raw, ticker)
    if not payload:
        return None
    return {"event_uid": event["uid"], "ticker": ticker,
            "payload": json.dumps({"ticker": ticker, **payload})}


def enrich_and_save(conn) -> int:
    """Compute earnings previews for matching events; replace the event_previews table."""
    import db
    db.init_db(conn)
    rows = [dict(r) for r in conn.execute(
        """SELECT uid, category_id, title, description, entity, event_date,
                  source, source_url, raw_json
           FROM events""")]
    previews = [p for p in (build_preview(r) for r in rows) if p]
    conn.execute("DELETE FROM event_previews")
    conn.commit()
    if previews:
        db.save_previews(conn, previews)
    return len(previews)


def _load_raw(raw_json: str | None) -> dict:
    if not raw_json:
        return {}
    try:
        return json.loads(raw_json)
    except Exception:
        return {}


def _event_ticker(raw: dict) -> str:
    row = raw.get("nfin_row") or raw
    ticker = str(row.get("symbol") or raw.get("ticker") or "").strip().upper()
    return ticker


def _money_to_float(value: str) -> float | None:
    text = str(value or "").replace("$", "").replace(",", "").strip()
    if not text or text.upper() == "N/A":
        return None
    mult = 1.0
    if text.endswith("T"):
        mult, text = 1_000_000_000_000.0, text[:-1]
    elif text.endswith("B"):
        mult, text = 1_000_000_000.0, text[:-1]
    elif text.endswith("M"):
        mult, text = 1_000_000.0, text[:-1]
    try:
        return float(text) * mult
    except ValueError:
        return None


def _importance_from_row(row: dict) -> tuple[str, str]:
    market_cap = _money_to_float(row.get("marketCap", ""))
    ests = int(str(row.get("noOfEsts") or "0").strip() or "0") if str(row.get("noOfEsts") or "").strip().isdigit() else 0
    if market_cap and market_cap >= 200_000_000_000:
        return "High", "High: large company, so the report can move the stock and sector mood."
    if market_cap and market_cap >= 50_000_000_000:
        return "Medium-high", "Medium-high: sizeable company with a meaningful stock-specific event."
    if ests >= 10:
        return "Medium", "Medium: enough analyst coverage to make the report useful to track."
    return "Low-medium", "Low-medium: useful as a company-specific update, but less likely to move the broad market."


def _time_label(value: str) -> str:
    labels = {
        "time-after-hours": "after the close",
        "time-pre-market": "before the open",
        "time-not-supplied": "time not supplied",
    }
    return labels.get(str(value or ""), str(value or "time not supplied").replace("time-", "").replace("-", " "))


def _build_scraped_preview(event: dict, raw: dict, ticker: str) -> dict | None:
    if event.get("source") != "nfin_earnings_calendar":
        return None
    row = raw.get("nfin_row") or {}
    if not row:
        return None

    company = row.get("name") or event.get("entity") or ticker
    confidence, significance = _importance_from_row(row)
    eps = row.get("epsForecast") or "not published"
    prior_eps = row.get("lastYearEPS") or "not available"
    fiscal_q = row.get("fiscalQuarterEnding") or "not supplied"
    ests = row.get("noOfEsts") or "not supplied"
    time = _time_label(row.get("time", ""))

    return {
        "company": company,
        "as_of": f"Scraped from nfin/Nasdaq on {raw.get('scraped_at', 'current run')}; reports {event.get('event_date')} ({time})",
        "decision": "Watch the report. The calendar gives the date and expectations, but not enough by itself for a directional call.",
        "confidence": confidence,
        "significance": significance,
        "implied_move": "",
        "avg_move": "",
        "lean": "Treat this as an event to monitor. A positive reaction needs a result or outlook that is clearly better than expectations.",
        "bar": [
            f"Profit target: {eps} per share",
            f"Analyst estimates counted: {ests}",
            f"Fiscal quarter: {fiscal_q}",
            f"Last year's profit per share: {prior_eps}",
        ],
        "watch": [
            "Does profit beat the target?",
            "Does management raise or lower its outlook?",
            "Does the stock move before the report, making expectations harder to beat?",
        ],
        "bull": "Better-than-expected profit plus a stronger outlook would support a positive reaction.",
        "bear": "A miss, weak outlook, or already-crowded run-up could pressure the stock.",
        "sources": [
            "https://nfin.dev/",
            event.get("source_url") or "https://api.nfin.dev/v1/calendar/earnings",
        ],
    }
