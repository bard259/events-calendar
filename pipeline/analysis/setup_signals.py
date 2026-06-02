"""Pre-event "setup" enrichment — flag high-asymmetry catalysts (VSCO/VSXY-style).

Before an outsized move on an earnings/strategic catalyst, three *leading*, publicly
visible signals tend to be present together:

  • SHORT INTEREST  — a heavily-shorted float is squeeze fuel when a beat lands.
  • ACTIVIST        — 13D/13D-A filers pushing change signal perceived undervaluation
                      AND a value-unlock catalyst.
  • ANALYST TREND   — price targets rising into the print = smart money leaning in.

Victoria's Secret (VSXY, ex-VSCO) on 2026-06-02 is the canonical example: ~19% of float
short + BBRC (12.9%) & Barington activists + a CEO-led turnaround + analysts lifting
targets → a Q1 blowout detonated a ~50% move (shorts covering amplified it).

Data sourcing note
------------------
Short interest, activist stakes, and analyst-target trends are NOT available from a free,
stdlib-friendly real-time API. `SETUP_PROFILES` is therefore a **sourced, dated snapshot**
(a small analyst watchlist) refreshed manually from public data — every entry carries an
`as_of` and `sources`. This is analytical *reference* data (like the rule tables in
`stock_impact.py`), NOT fabricated event data, so it does not violate the "no synthetic
events" rule. A live refresher for the activist leg via SEC EDGAR full-text search is
provided (`verify_activist_edgar`) but is not run by default (keeps collection offline-fast).

Output per matched event: an `asymmetry_score` (0–100) + label + human-readable notes,
stored in `event_setups` and surfaced in the app as a ⚡ SETUP badge.
"""
from __future__ import annotations

import json
import re

from analysis.stock_impact import ENTITY_TICKERS

# ── Sourced setup snapshot (refresh periodically; keep `as_of` + `sources` honest) ──
# short_pct = short interest as % of float (None if not pinned down).
# analyst_trend ∈ {"rising","steady","falling",None}.
SETUP_PROFILES: dict[str, dict] = {
    "VSXY": {
        "company": "Victoria's Secret",
        "short_pct": 19.0, "short_as_of": "2026-05 (pre-Q1, Ortex)",
        "activists": ["BBRC / Brett Blundy (12.9%)", "Barington Capital"],
        "activist_since": "2025-05", "analyst_trend": "rising",
        "thesis": "Core bra/PINK turnaround under CEO Hillary Super; 4 straight quarters of "
                  "positive comps; activists pushing board refresh + value unlock.",
        "sources": [
            "https://www.cnbc.com/2025/06/21/how-activist-barington-can-collaborate-with-victorias-secret-to-improve-value.html",
            "https://www.sec.gov/Archives/edgar/data/0001856437/000121390026051617/ea028885801ex99-4.htm",
            "https://fintel.io/ss/us/vsco",
        ],
        "realized": "+~50% on 2026-06-02 Q1 beat + raised guidance (the worked example).",
    },
    "KSS": {
        "company": "Kohl's",
        "short_pct": 31.0, "short_as_of": "2026-04-30 settlement (range 24–44% across sources)",
        "activists": ["Macellum (prior campaign)"],
        "activist_since": "2021", "analyst_trend": "steady",
        "thesis": "Margin-led turnaround; Q1-2026 beat (EPS -0.13 vs -0.20 est); repeated "
                  "short-squeeze history on any positive surprise.",
        "sources": [
            "https://www.marketbeat.com/stocks/NYSE/KSS/short-interest/",
            "https://www.benzinga.com/markets/earnings/26/05/52850607/short-squeeze-and-earnings-why-kohls-stock-spiked-thursday",
            "https://fintel.io/ss/us/kss",
        ],
    },
    "CTRN": {
        "company": "Citi Trends",
        "short_pct": 9.79, "short_as_of": "2026-05-15 (MarketBeat/FINRA; ~7.2 days-to-cover, rising)",
        "activists": [],  # Macellum won board seats in 2021; no active 2026 campaign confirmed
        "activist_since": None, "analyst_trend": None,
        "thesis": "Small-cap value-apparel turnaround — 21 consecutive months of positive comps "
                  "and expanding profitability; small float + rising short ratio (prior Macellum "
                  "board win 2021). Milder version of the VSXY setup.",
        "sources": [
            "https://www.marketbeat.com/stocks/NASDAQ/CTRN/short-interest/",
            "https://www.fool.com/earnings/call-transcripts/2026/06/02/citi-trends-ctrn-q1-2026-earnings-transcript/",
        ],
    },
    "M": {
        "company": "Macy's",
        "short_pct": None, "short_as_of": "elevated (not pinned)",
        "activists": ["Barington Capital (2025)", "Arkhouse / Brigade (ended 2024)"],
        "activist_since": "2024", "analyst_trend": "steady",
        "thesis": "Real-estate value-unlock pressure + self-led 'Bold New Chapter' turnaround; "
                  "recurrent activist interest.",
        "sources": [
            "https://www.crainsnewyork.com/retail/macys-new-activist-investor-wants-retailer-create-real-estate-arm",
            "https://www.foxbusiness.com/markets/macys-activist-investors-want-retailer-make-significant-changes",
        ],
    },
}

# Earnings / guidance catalyst keywords (the event type that converts a setup into a move).
_EARNINGS_KW = re.compile(
    r"\b(earnings|results|quarterly|q[1-4]\b|fiscal|guidance|outlook|report[s]?)\b", re.I)
_STRATEGIC_KW = re.compile(
    r"\b(investor day|capital markets day|launch|unveil|spin-?off|merger|acquisition|review)\b", re.I)

# Resolve a primary ticker from an event the same way stock_impact's entity layer does
# (longest fragment wins so "super micro" beats "micro").
_TICKER_INDEX = sorted(ENTITY_TICKERS.items(), key=lambda kv: -len(kv[0]))


def primary_ticker(blob: str) -> str:
    b = blob.lower()
    for frag, ticker in _TICKER_INDEX:
        if frag in b:
            return ticker
    return ""


def score_setup(profile: dict, category_id: int, blob: str) -> dict:
    """Combine the leading signals + this event's catalyst type into a 0–100 asymmetry score."""
    score = 0
    notes: list[str] = []

    sp = profile.get("short_pct")
    if sp is not None:
        score += round(min(sp, 40) / 40 * 45)  # short interest: up to 45 pts
        if sp >= 20:
            notes.append(f"{sp:.0f}% of float short — squeeze fuel on a beat")
        else:
            notes.append(f"{sp:.0f}% of float short")

    activists = profile.get("activists") or []
    if activists:
        score += 25
        notes.append("Activist(s): " + ", ".join(activists))

    is_earnings = category_id == 3 or bool(_EARNINGS_KW.search(blob))
    is_strategic = category_id in (4, 9) or bool(_STRATEGIC_KW.search(blob))
    if is_earnings:
        score += 20
        notes.append("Earnings/guidance catalyst — binary, expectations resettable")
    elif is_strategic:
        score += 12
        notes.append("Strategic catalyst")
    else:
        score += 4

    trend = profile.get("analyst_trend")
    if trend == "rising":
        score += 12
        notes.append("Analyst targets rising into the print")
    elif trend == "falling":
        score -= 8
        notes.append("Analyst targets falling")

    if profile.get("thesis"):
        notes.append("Turnaround thesis: " + profile["thesis"])

    score = max(0, min(100, score))
    label = ("High-asymmetry setup" if score >= 70
             else "Notable setup" if score >= 45
             else "Low")
    bias = "Upside-skew on a beat; sharp downside on a miss (two-sided, high vol)"
    return {"score": score, "label": label, "bias": bias, "notes": notes}


def build_setup(event: dict) -> dict | None:
    """Return a setup row for an event whose ticker is in SETUP_PROFILES, else None."""
    blob = f"{event.get('title','')} {event.get('description','')} {event.get('entity','')}"
    ticker = primary_ticker(blob)
    profile = SETUP_PROFILES.get(ticker)
    if not profile:
        return None
    scored = score_setup(profile, event.get("category_id", 0), blob)
    return {
        "event_uid": event["uid"],
        "ticker": ticker,
        "score": scored["score"],
        "label": scored["label"],
        "short_pct": profile.get("short_pct"),
        "short_as_of": profile.get("short_as_of", ""),
        "activists": json.dumps(profile.get("activists") or []),
        "analyst_trend": profile.get("analyst_trend") or "",
        "bias": scored["bias"],
        "notes": json.dumps(scored["notes"]),
        "sources": json.dumps(profile.get("sources") or []),
    }


def enrich_and_save(conn) -> int:
    """Compute setups for every event with a profiled ticker; replace the event_setups table.

    Pure in-memory + DB (no network) — safe to run on every collection. Returns count.
    """
    import db  # local import to avoid a cycle
    db.init_db(conn)  # ensure event_setups exists
    rows = [dict(r) for r in conn.execute(
        "SELECT uid, category_id, title, description, entity FROM events")]
    setups = [s for s in (build_setup(r) for r in rows) if s]
    conn.execute("DELETE FROM event_setups")
    conn.commit()
    if setups:
        db.save_setups(conn, setups)
    return len(setups)


# ── Optional live refresher (NOT called by default) ─────────────────────────────
def verify_activist_edgar(http, company: str, since: str = "2025-01-01",
                          until: str = "2026-12-31") -> list[dict]:
    """Live check: recent SC 13D / 13D-A activist filings mentioning `company` (SEC EDGAR FTS).

    Use to refresh the `activists` field with real, dated filings. Returns FTS hit dicts.
    """
    import edgar_fts
    hits = []
    for form in ("SC 13D/A", "SC 13D"):
        hits += edgar_fts.search(http, company, forms=form, startdt=since, enddt=until, limit=5)
    return hits
