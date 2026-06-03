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
        "as_of": "2026-06-03 — PRE-PRINT FINAL CHECK; Q2 FY26 results PENDING (~5 PM ET today, "
                 "move plays 6/4). NOTE: original 6/2 bar had a baseline error — 'Q1 AI ~$4.1B' "
                 "was Q4 FY2024 data; actual Q1 FY2026 AI revenue was $8.4B (+106% YoY). "
                 "Bar and watch updated with corrected figures.",
        "implied_move": "±8–10.6%",
        "avg_move": "±6.7% (last 4 quarters)",
        "lean": "RESULTS PENDING — beat-and-raise highly likely but PRICE reaction two-sided and "
                "sell-the-news risk NOW ELEVATED FURTHER: stock ran up ~$280B in market cap over "
                "4 sessions into the print; ATH moved to ~$495 (original preview anchored $447–466). "
                "Up +4.7% on 6/3 alone before results. Leans UP only on beat + raised Q3 guide + "
                "FY2027 $100B+ AI reiteration. In-line with guide = risk-off. "
                "KEY LEARNING (pre-print): original AI-semi bar was 2×+ too low; $10.7B guided "
                "Q2 AI rev is the real floor, not $5.0B.",
        "bar": [
            "EPS consensus $2.40 (+52% YoY; revised up from ~$2.16 at Q1 print)",
            "Revenue $22.1B consensus / $22.0B company guide (+47% YoY); semi segment ~$14.8B (+76%)",
            "AI semis: Q1 FY26 ACTUAL $8.4B (+106% YoY) → Q2 FY26 company GUIDE $10.7B (+140% YoY)",
            "CORRECTED BASELINE: original preview cited 'Q1 ~$4.1B' — that was Q4 FY2024, NOT Q1 FY26",
            "Buy-side whisper for AI rev likely $11B+; $10.7B is the floor, not the stretch target",
            "Infrastructure software (VMware) ~$7.3B; adj. EBITDA margin ~68% guided",
        ],
        "watch": [
            "Q3 FY26 AI-semiconductor guide vs whisper $11B+ (single biggest swing factor)",
            "FY2027 $100B+ AI revenue reiteration / line-of-sight update from Hock Tan",
            "New hyperscaler custom-XPU/ASIC design-win disclosures (Alphabet, Meta, Apple rumored)",
            "Gross-margin mix (AI semis skew rich; VMware software margins watch)",
        ],
        "bull": "AI franchise compounding — 3 hyperscaler XPU partnerships confirmed, $100B+ 2027 "
                "visibility; Q1 beat raised bar and stock still added ~$280B pre-Q2; Oppenheimer, "
                "Susquehanna, MS, JPM all raised targets into print; beat-and-raise would confirm "
                "the AI-ASIC supercycle thesis for a new leg higher.",
        "bear": "Stock at ~$495 ATH, up ~+4.7% on 6/3 alone, +40%+ YTD — an aggressive beat is "
                "already priced; even a clean in-line on AI revenue ($10.7B) with modest Q3 guide "
                "could trigger 'sell the news.' Pre-earnings rally means the implied ±8–10.6% "
                "downside scenario starts from a much higher base than the original $447–466.",
        "contrast": "Mirror image of the VSXY setup: crowded-long at highs + high expectations = "
                    "asymmetry skewed to DOWNSIDE surprise (VSXY was shorted/doubted → upside). "
                    "Now even more extreme given the +$280B four-session pre-print rally.",
        "learning": [
            "BASELINE ERROR IN ORIGINAL PREVIEW: 'Q1 AI ~$4.1B' was Q4 FY2024 data — "
            "actual Q1 FY2026 AI revenue was $8.4B (+106% YoY, reported March 4 2026). "
            "The '$5.0B buy-side bar' for Q2 was 2x+ too low; company itself guided $10.7B. "
            "When refreshing previews, always pull the most recent actual quarterly print, "
            "not calendar-year comparisons or prior-cycle figures.",
            "PRE-EARNINGS RALLY RISK: Original preview noted ATH ~$447–466 and sell-the-news risk. "
            "By print day (6/3), stock had reached ~$495 ATH with +$280B four-session market-cap "
            "gain. The structural lean was correct but the reference price was stale by ~10%; "
            "update ATH/price anchors each refresh cycle, not just the estimates.",
            "RESULTS PENDING — update lean, bar, and learning fields after 6/3 close with actuals.",
        ],
        "sources": [
            "https://news.alphastreet.com/broadcom-avgo-q2-2026-preview-eps-est-2-40-reports-june-3/amp/",
            "https://www.tipranks.com/news/broadcom-is-about-to-report-q2-earnings-options-traders-expect-a-10-65-move-in-avgo-stock",
            "https://www.heygotrade.com/en/blog/broadcom-avgo-q2-fy26-earnings-preview/",
            "https://www.marketbeat.com/stocks/NASDAQ/AVGO/forecast/",
            "https://www.cnbc.com/2026/03/04/broadcom-avgo-q1-earnings-report-2026.html",
            "https://investors.broadcom.com/news-releases/news-release-details/broadcom-inc-announces-first-quarter-fiscal-year-2026-financial",
            "https://seekingalpha.com/news/4599887-broadcom-q2-2026-earnings-preview",
            "https://www.bloomberg.com/news/articles/2026-06-03/broadcom-s-280-billion-four-day-bonanza-to-get-earnings-check",
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
