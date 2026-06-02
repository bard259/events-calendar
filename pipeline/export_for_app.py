"""Export collected events + stock impacts from SQLite to app/assets/events.json."""
from __future__ import annotations

import json

import db
from config import APP_DATA_PATH, CATEGORIES, TARGET_MONTH


def main():
    conn = db.connect()
    rows = conn.execute(
        """SELECT uid, category_id, category, title, description, event_date,
                  event_datetime, entity, importance, source, source_type, source_url,
                  pub_date, pub_source, collected_at
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
