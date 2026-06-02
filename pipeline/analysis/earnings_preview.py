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
        "implied_move": "±8–10.6%",
        "avg_move": "±6.7% (last 4 quarters)",
        "lean": "Beat highly likely; PRICE reaction two-sided. Leans UP only on a beat-and-raise "
                "of the forward AI guide — elevated sell-the-news risk at all-time highs.",
        "bar": [
            "EPS consensus $2.40 (+52% YoY; revised up from $2.16 over 90 days)",
            "Revenue ~$22.1B (company guided ~$22B, +47% YoY)",
            "AI semis: Q1 ~$4.1B → buy-side bar ~$5.0B; whisper higher (WFC: AI +30–40% vs prior)",
        ],
        "watch": [
            "NEXT-quarter AI-semiconductor guide vs. the ~$5B+ whisper (the key swing factor)",
            "New hyperscaler custom-XPU/ASIC design wins; 2027 AI backlog tone",
            "Gross-margin mix (semis vs. VMware/infrastructure software)",
        ],
        "bull": "AI franchise + estimates revised up + guide already above consensus; Strong Buy, "
                "avg target ~$482 (WFC $545); historically drifts higher in 6 of last 8 post-prints.",
        "bear": "At all-time highs (~$447–466), +29% YTD, ran up ~5% into the print → a beat is "
                "largely priced; an in-line AI guide could trigger profit-taking. '$100B vol warning.'",
        "contrast": "Mirror image of the VSXY setup: crowded-long at highs + high expectations = "
                    "asymmetry skewed to DOWNSIDE surprise (VSXY was shorted/doubted → upside).",
        "sources": [
            "https://news.alphastreet.com/broadcom-avgo-q2-2026-preview-eps-est-2-40-reports-june-3/amp/",
            "https://www.tipranks.com/news/broadcom-is-about-to-report-q2-earnings-options-traders-expect-a-10-65-move-in-avgo-stock",
            "https://www.heygotrade.com/en/blog/broadcom-avgo-q2-fy26-earnings-preview/",
            "https://www.marketbeat.com/stocks/NASDAQ/AVGO/forecast/",
        ],
    },
}


def build_preview(event: dict) -> dict | None:
    """Return a preview row for an earnings event whose ticker is in PREVIEWS, else None."""
    blob = f"{event.get('title','')} {event.get('description','')} {event.get('entity','')}"
    if not _EARNINGS_KW.search(blob):
        return None
    ticker = primary_ticker(blob)
    payload = PREVIEWS.get(ticker)
    if not payload:
        return None
    return {"event_uid": event["uid"], "ticker": ticker,
            "payload": json.dumps({"ticker": ticker, **payload})}


def enrich_and_save(conn) -> int:
    """Compute earnings previews for matching events; replace the event_previews table."""
    import db
    db.init_db(conn)
    rows = [dict(r) for r in conn.execute(
        "SELECT uid, category_id, title, description, entity FROM events")]
    previews = [p for p in (build_preview(r) for r in rows) if p]
    conn.execute("DELETE FROM event_previews")
    conn.commit()
    if previews:
        db.save_previews(conn, previews)
    return len(previews)
