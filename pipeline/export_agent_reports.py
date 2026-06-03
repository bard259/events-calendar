"""Export decision/critic agent reports and performance data for the app."""
from __future__ import annotations

import json
from pathlib import Path

import db
from config import ROOT_DIR

OUT_PATH = ROOT_DIR / "app" / "assets" / "agent_reports.json"


def _read(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    try:
        return p.read_text()
    except Exception:
        return ""


def _rows(conn, sql: str, args=()):
    return [dict(r) for r in conn.execute(sql, args).fetchall()]


def _snapshots(conn, decision_ids: list[int]) -> dict[int, dict]:
    if not decision_ids:
        return {}
    placeholders = ",".join("?" for _ in decision_ids)
    rows = _rows(conn, f"""
        SELECT * FROM investment_price_snapshots
        WHERE decision_id IN ({placeholders})
        ORDER BY decision_id, snapshot_date, id
    """, decision_ids)
    grouped: dict[int, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["decision_id"], []).append(r)
    out = {}
    for did, snaps in grouped.items():
        priced = [s for s in snaps if s.get("price") is not None]
        first = priced[0] if priced else None
        latest = priced[-1] if priced else None
        ret = None
        if first and latest and first["price"]:
            ret = (latest["price"] - first["price"]) / first["price"] * 100
        out[did] = {
            "first": first,
            "latest": latest,
            "return_pct": ret,
            "snapshot_count": len(snaps),
        }
    return out


def main():
    conn = db.connect()
    db.init_db(conn)
    decision_runs = _rows(conn, "SELECT * FROM decision_agent_runs ORDER BY id DESC LIMIT 20")
    critic_runs = _rows(conn, "SELECT * FROM decision_critic_runs ORDER BY id DESC LIMIT 20")
    latest_decision_run = decision_runs[0] if decision_runs else None
    latest_critic_run = critic_runs[0] if critic_runs else None

    decisions = []
    if latest_decision_run:
        decisions = _rows(conn, """
            SELECT * FROM investment_decisions
            WHERE run_id=?
            ORDER BY score DESC, event_date, ticker
        """, (latest_decision_run["id"],))
    perf = _snapshots(conn, [d["id"] for d in decisions])
    for d in decisions:
        d["performance"] = perf.get(d["id"], {
            "first": None, "latest": None, "return_pct": None, "snapshot_count": 0,
        })

    findings = []
    if latest_critic_run:
        findings = _rows(conn, """
            SELECT * FROM decision_critic_findings
            WHERE run_id=?
            ORDER BY severity DESC, id DESC
        """, (latest_critic_run["id"],))

    action_counts = {}
    for d in decisions:
        action_counts[d["action"]] = action_counts.get(d["action"], 0) + 1
    tracked = [d for d in decisions if d["action"] in ("BUY", "WATCH")]
    measured = [d for d in tracked if d["performance"]["return_pct"] is not None]
    avg_return = None
    if measured:
        avg_return = sum(d["performance"]["return_pct"] for d in measured) / len(measured)

    memory_path = ROOT_DIR / "pipeline" / "memory" / "key_knowledge_memory.json"
    try:
        memory = json.loads(memory_path.read_text())
    except Exception:
        memory = {}

    payload = {
        "decision_runs": decision_runs,
        "critic_runs": critic_runs,
        "latest_decision_report": _read(latest_decision_run.get("report_path") if latest_decision_run else None),
        "latest_critic_report": _read(latest_critic_run.get("report_path") if latest_critic_run else None),
        "latest_decisions": decisions,
        "latest_findings": findings,
        "memory": memory,
        "performance": {
            "action_counts": action_counts,
            "tracked_count": len(tracked),
            "measured_count": len(measured),
            "pending_count": len(tracked) - len(measured),
            "avg_return_pct": avg_return,
        },
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    conn.close()
    print(f"Exported agent reports -> {OUT_PATH}")


if __name__ == "__main__":
    main()
