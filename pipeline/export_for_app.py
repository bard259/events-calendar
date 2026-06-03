"""Export collected events + stock impacts from SQLite to app/assets/events.json."""
from __future__ import annotations

import json
import re

import db
from config import APP_DATA_PATH, CATEGORIES, TARGET_MONTH
from company_tldr import COMPANY_TLDR
from analysis.setup_signals import primary_ticker


EARNINGS_SOURCE = "nfin_earnings_calendar"


def _raw_nfin_row(ev: dict) -> dict:
    if ev.get("source") != EARNINGS_SOURCE:
        return {}
    try:
        raw = json.loads(ev.get("raw_json") or "{}")
    except Exception:
        return {}
    return raw.get("nfin_row") or {}


def _money_label(value: str) -> str:
    text = str(value or "").strip()
    if not text or text.upper() == "N/A":
        return ""
    compact = re.sub(r"[$,]", "", text)
    try:
        if compact.endswith("T"):
            return f"${float(compact[:-1]):.1f}T"
        if compact.endswith("B"):
            return f"${float(compact[:-1]):.1f}B"
        if compact.endswith("M"):
            return f"${float(compact[:-1]):.1f}M"
        amount = float(compact)
    except ValueError:
        return text
    if amount >= 1_000_000_000_000:
        return f"${amount / 1_000_000_000_000:.1f}T"
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.1f}M"
    return text


def _market_cap_value(value) -> float:
    compact = re.sub(r"[$,]", "", str(value or "").strip())
    mult = 1.0
    if compact[-1:].upper() == "T":
        mult, compact = 1e12, compact[:-1]
    elif compact[-1:].upper() == "B":
        mult, compact = 1e9, compact[:-1]
    elif compact[-1:].upper() == "M":
        mult, compact = 1e6, compact[:-1]
    try:
        return float(compact) * mult
    except ValueError:
        return 0.0


def _size_label(value) -> str:
    v = _market_cap_value(value)
    if v >= 200e9:
        return "mega-cap"
    if v >= 10e9:
        return "large-cap"
    if v >= 2e9:
        return "mid-cap"
    if v > 0:
        return "small-cap"
    return ""


def _resolve_ticker(ev: dict) -> str:
    """The company's own ticker: nfin symbol if present, else the entity → ticker map."""
    sym = str(_raw_nfin_row(ev).get("symbol") or "").strip().upper()
    if sym:
        return sym
    entity = ev.get("entity") or ""
    return primary_ticker(entity).upper() if entity else ""


def _company_intro(ev: dict) -> str:
    """A plain-English company TL;DR for the card.

    Prefers a curated business/mission one-liner (company_tldr.COMPANY_TLDR). For the
    long-tail earnings calendar, falls back to a clean "{name} ({ticker}) — {size}-cap
    company" line (much less technical than dumping market value + estimate counts).
    Returns "" for events with no resolvable company (macro, launches, geopolitics).
    """
    ticker = _resolve_ticker(ev)
    tldr = COMPANY_TLDR.get(ticker, "")
    if tldr:
        return tldr

    row = _raw_nfin_row(ev)
    if not row:
        return ""
    company = str(row.get("name") or ev.get("entity") or "").strip()
    if not company:
        return ""
    lead = f"{company} ({ticker})" if ticker else company
    size = _size_label(row.get("marketCap") or "")
    return f"{lead} — {size} company." if size else f"{lead} — public company."


def main():
    conn = db.connect()
    rows = conn.execute(
        """SELECT uid, category_id, category, title, description, event_date,
                  event_datetime, entity, importance, source, source_type, source_url,
                  pub_date, pub_source, collected_at, raw_json
           FROM events ORDER BY event_date, category_id"""
    ).fetchall()
    events = [dict(r) for r in rows]

    # Attach stock impacts per event
    impacts_raw = conn.execute(
        "SELECT event_uid, ticker, direction, confidence, reason, sector FROM event_stock_impacts"
    ).fetchall()
    impacts_by_uid: dict[str, list] = {}
    for imp in impacts_raw:
        impacts_by_uid.setdefault(imp["event_uid"], []).append({
            "ticker": imp["ticker"], "direction": imp["direction"],
            "confidence": imp["confidence"], "reason": imp["reason"],
            "sector": imp["sector"],
        })
    for ev in events:
        ev["stock_impacts"] = impacts_by_uid.get(ev["uid"], [])

    # Attach pre-event "setup" (short interest / activist / asymmetry score) where present
    setups_by_uid: dict[str, dict] = {}
    try:
        for s in conn.execute(
            """SELECT event_uid, ticker, score, label, short_pct, short_as_of,
                      activists, analyst_trend, bias, notes, sources FROM event_setups"""):
            setups_by_uid[s["event_uid"]] = {
                "ticker": s["ticker"], "score": s["score"], "label": s["label"],
                "short_pct": s["short_pct"], "short_as_of": s["short_as_of"],
                "activists": json.loads(s["activists"] or "[]"),
                "analyst_trend": s["analyst_trend"],
                "bias": s["bias"],
                "notes": json.loads(s["notes"] or "[]"),
                "sources": json.loads(s["sources"] or "[]"),
            }
    except Exception:
        pass  # event_setups table may not exist on an older DB
    for ev in events:
        if ev["uid"] in setups_by_uid:
            ev["setup"] = setups_by_uid[ev["uid"]]

    # Attach earnings-preview annotations (consensus bar / implied move / lean) where present
    previews_by_uid: dict[str, dict] = {}
    try:
        for p in conn.execute("SELECT event_uid, payload FROM event_previews"):
            previews_by_uid[p["event_uid"]] = json.loads(p["payload"])
    except Exception:
        pass  # event_previews table may not exist on an older DB
    for ev in events:
        if ev["uid"] in previews_by_uid:
            ev["preview"] = previews_by_uid[ev["uid"]]
        intro = _company_intro(ev)
        if intro:
            ev["company_intro"] = intro
        ev.pop("raw_json", None)

    payload = {
        "month": TARGET_MONTH,
        "generated_events": len(events),
        "categories": [{"id": k, "name": v} for k, v in CATEGORIES.items()],
        "events": events,
    }
    APP_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    APP_DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    conn.close()
    print(f"Exported {len(events)} events → {APP_DATA_PATH}")


if __name__ == "__main__":
    main()
