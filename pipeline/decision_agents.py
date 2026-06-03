"""Decision and critic agents for earnings-preview workflows.

These agents are rules-based and auditable. They make paper investment decisions from
earnings previews + a small key-knowledge memory, then critique prior decisions and update
that memory. They do not place trades.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import db
from config import PIPELINE_DIR
from http_client import HttpClient
from models import CollectorReport

MEMORY_PATH = PIPELINE_DIR / "memory" / "key_knowledge_memory.json"
REPORT_DIR = PIPELINE_DIR / "reports"


DEFAULT_MEMORY = {
    "version": 1,
    "updated_at": "",
    "principles": [
        "Make a positive call when several independent signals line up; do not require perfection.",
        "Penalize data-quality warnings, unverified dates, and already-reported stale events.",
        "Treat earnings as two-sided unless the preview says the outlook is likely to improve.",
        "A large run-up is acceptable when a new external validation resets the addressable market.",
        "AI infrastructure momentum matters most when endorsement, custom silicon, optical networking, and guidance all point the same way.",
        "Record missed high-significance opportunities so future scoring learns from omissions.",
    ],
    "weights": {
        "confidence_high": 34,
        "confidence_medium": 21,
        "confidence_low": 5,
        "significance_high": 29,
        "significance_medium": 17,
        "setup_high": 22,
        "setup_notable": 12,
        "data_quality_penalty": -45,
        "generic_preview_penalty": -3,
        "ai_infra_momentum": 18,
        "positive_outlook": 14,
    },
    "lessons": [],
}


def today_iso() -> str:
    return date.today().isoformat()


def load_memory(path: Path = MEMORY_PATH) -> dict:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        save_memory(DEFAULT_MEMORY.copy(), path)
    try:
        return json.loads(path.read_text())
    except Exception:
        backup = path.with_suffix(".broken.json")
        path.replace(backup)
        mem = DEFAULT_MEMORY.copy()
        mem["lessons"].append({
            "date": today_iso(),
            "lesson": f"Memory file was unreadable and was moved to {backup.name}.",
            "source": "critic",
        })
        save_memory(mem, path)
        return mem


def save_memory(memory: dict, path: Path = MEMORY_PATH):
    memory["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(memory, ensure_ascii=False, indent=2))


def parse_payload(text: str) -> dict:
    try:
        return json.loads(text or "{}")
    except Exception:
        return {}


def _score_phrase(value: str, high: int, medium: int, low: int) -> int:
    v = (value or "").lower()
    if "high" in v:
        return high
    if "low-medium" in v:
        return round((low + medium) / 2)
    if "medium" in v:
        return medium
    if "low" in v:
        return low
    return 10


def _has_any(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def _action(score: int, text: str) -> str:
    if _has_any(text, ["ignore", "wrong", "unverified", "do not rely", "already reported"]):
        return "IGNORE"
    if score >= 56:
        return "BUY"
    if score >= 40:
        return "WATCH"
    return "PASS"


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
    except Exception:
        return None


def _event_rows(conn, run_date: str, horizon_days: int) -> list[dict]:
    start = date.fromisoformat(run_date)
    end = start + timedelta(days=horizon_days)
    rows = conn.execute(
        """SELECT e.uid, e.event_date, e.title, e.entity, e.source, e.source_url,
                  e.raw_json, p.ticker, p.payload,
                  s.score AS setup_score, s.label AS setup_label
           FROM event_previews p
           JOIN events e ON e.uid = p.event_uid
           LEFT JOIN event_setups s ON s.event_uid = e.uid
           WHERE e.event_date BETWEEN ? AND ?
           ORDER BY e.event_date, e.importance DESC, p.ticker""",
        (start.isoformat(), end.isoformat()),
    ).fetchall()
    return [dict(r) for r in rows]


def make_decision(row: dict, memory: dict) -> dict:
    payload = parse_payload(row["payload"])
    raw = parse_payload(row.get("raw_json"))
    source_row = raw.get("nfin_row") or {}
    weights = memory.get("weights", DEFAULT_MEMORY["weights"])
    text = " ".join(str(payload.get(k, "")) for k in (
        "decision", "confidence", "significance", "lean", "bull", "bear", "watch", "bar", "as_of"))
    event_text = " ".join(str(row.get(k, "")) for k in ("title", "entity", "source"))

    score = 0
    score += _score_phrase(payload.get("confidence", ""), weights["confidence_high"],
                           weights["confidence_medium"], weights["confidence_low"])
    score += _score_phrase(payload.get("significance", ""), weights["significance_high"],
                           weights["significance_medium"], 6)

    setup_score = row.get("setup_score") or 0
    if setup_score >= 70:
        score += weights["setup_high"]
    elif setup_score >= 45:
        score += weights["setup_notable"]

    if _has_any(text, ["wrong", "unverified", "do not rely", "already reported"]):
        score += weights["data_quality_penalty"]
    if row.get("source") == "nfin_earnings_calendar":
        score += weights["generic_preview_penalty"]

    cap = _money_to_float(source_row.get("marketCap", ""))
    if cap and cap >= 1_000_000_000_000:
        score += 8
    elif cap and cap >= 200_000_000_000:
        score += 5

    if _has_any(text, ["raises its ai outlook", "stronger outlook", "turnaround looks real", "raised"]):
        score += weights.get("positive_outlook", 14)
    if ai_infra_momentum_score(row["ticker"], text + " " + event_text) >= 3:
        score += weights.get("ai_infra_momentum", 18)
    if _has_any(text, ["near highs", "merely good", "weak outlook", "miss", "lowered"]):
        score -= 6

    score = max(0, min(100, int(score)))
    action = _action(score, text)
    thesis = payload.get("decision") or payload.get("lean") or "Watch earnings versus expectations."
    risks = payload.get("bear") or "Earnings are two-sided; a miss or weak outlook can reverse the setup."
    return {
        "event_uid": row["uid"],
        "event_date": row["event_date"],
        "ticker": row["ticker"],
        "company": payload.get("company") or row.get("entity") or row["ticker"],
        "action": action,
        "confidence": payload.get("confidence", ""),
        "significance": payload.get("significance", ""),
        "score": score,
        "thesis": thesis,
        "risks": risks,
        "payload": payload,
        "source": row.get("source", ""),
        "setup_score": setup_score,
        "ai_infra_momentum": ai_infra_momentum_score(row["ticker"], text + " " + event_text),
    }


AI_INFRA_TICKERS = {
    "MRVL", "AVGO", "CRDO", "ANET", "CIEN", "COHR", "LITE", "GLW",
    "VRT", "DELL", "SMCI", "HPE", "CSCO", "ALAB", "VST", "ETN",
}


def ai_infra_momentum_score(ticker: str, text: str) -> int:
    """Score Marvell-like AI-infrastructure momentum signals."""
    if ticker not in AI_INFRA_TICKERS:
        return 0
    checks = [
        ["nvidia", "jensen", "nvlink", "partnership", "endorsement"],
        ["custom silicon", "asic", "xpu", "ai chip", "accelerator"],
        ["optical", "photonics", "interconnect", "dsp", "ethernet", "networking"],
        ["hyperscaler", "data center", "cloud", "ai infrastructure"],
        ["raised", "beat", "guidance", "price target", "analyst"],
    ]
    t = text.lower()
    return sum(1 for group in checks if any(term in t for term in group))


def run_decision_agent(run_date: str | None = None, horizon_days: int = 7) -> dict:
    run_date = run_date or today_iso()
    memory = load_memory()
    conn = db.connect()
    db.init_db(conn)
    run_id = db.start_decision_run(conn, run_date, horizon_days, str(MEMORY_PATH))
    rows = _event_rows(conn, run_date, horizon_days)
    decisions = _dedupe_decisions([make_decision(r, memory) for r in rows])

    created_at = datetime.now(timezone.utc).isoformat()
    memory_snapshot = json.dumps({
        "version": memory.get("version"),
        "principles": memory.get("principles", []),
        "weights": memory.get("weights", {}),
        "recent_lessons": memory.get("lessons", [])[-5:],
    }, ensure_ascii=False)
    db.save_investment_decisions(conn, [{
        "run_id": run_id,
        "run_date": run_date,
        "event_uid": d["event_uid"],
        "event_date": d["event_date"],
        "ticker": d["ticker"],
        "company": d["company"],
        "action": d["action"],
        "confidence": d["confidence"],
        "significance": d["significance"],
        "score": d["score"],
        "thesis": d["thesis"],
        "risks": d["risks"],
        "memory_snapshot": memory_snapshot,
        "created_at": created_at,
    } for d in decisions])

    report_path = write_decision_report(run_date, horizon_days, decisions, memory)
    db.finish_decision_run(conn, run_id, events_reviewed=len(rows),
                           decisions_made=len(decisions), report_path=str(report_path),
                           notes=["Paper decisions only; no trades are placed."])
    conn.close()
    return {"run_id": run_id, "report_path": report_path, "decisions": decisions}


def _dedupe_decisions(decisions: list[dict]) -> list[dict]:
    """Collapse duplicate ticker/date reports from multiple sources into the strongest row."""
    best: dict[tuple[str, str], dict] = {}
    for d in decisions:
        key = (d["ticker"], d["event_date"])
        cur = best.get(key)
        if cur is None or d["score"] > cur["score"]:
            best[key] = d
    return sorted(best.values(), key=lambda d: (d["event_date"], -d["score"], d["ticker"]))


def write_decision_report(run_date: str, horizon_days: int, decisions: list[dict], memory: dict) -> Path:
    out_dir = REPORT_DIR / "decisions"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_date}.md"
    buys = [d for d in decisions if d["action"] == "BUY"]
    watches = [d for d in decisions if d["action"] == "WATCH"]
    ignores = [d for d in decisions if d["action"] == "IGNORE"]
    top = sorted(decisions, key=lambda d: (-d["score"], d["event_date"], d["ticker"]))[:25]
    lines = [
        f"# Decision Agent Report — {run_date}",
        "",
        "Paper investment decisions from earnings previews and key memory. No trades are placed.",
        "",
        f"Window: {run_date} through +{horizon_days} days",
        f"Reviewed: {len(decisions)} earnings previews",
        f"BUY: {len(buys)} · WATCH: {len(watches)} · PASS: {sum(d['action']=='PASS' for d in decisions)} · IGNORE: {len(ignores)}",
        "",
        "## Top Decisions",
    ]
    for d in top:
        lines += [
            f"- **{d['action']} {d['ticker']}** ({d['event_date']}, score {d['score']}) — {d['company']}",
            f"  - Decision: {d['thesis']}",
            f"  - Confidence: {d['confidence'] or 'n/a'}",
            f"  - Significance: {d['significance'] or 'n/a'}",
            f"  - Key risk: {d['risks']}",
        ]
    lines += ["", "## Memory Used"]
    for p in memory.get("principles", []):
        lines.append(f"- {p}")
    path.write_text("\n".join(lines) + "\n")
    return path


def _outcome_hint(text: str) -> str:
    t = text.lower()
    if _has_any(t, ["strongly positive", "jumped", "surged", "beat", "raised", "turnaround looks real"]):
        return "positive"
    if _has_any(t, ["weak", "miss", "lowered", "wrong", "ignore", "do not rely"]):
        return "negative_or_bad_data"
    return "unknown"


def run_critic_agent(run_date: str | None = None, lookback_days: int = 14) -> dict:
    run_date = run_date or today_iso()
    memory = load_memory()
    conn = db.connect()
    db.init_db(conn)
    run_id = db.start_critic_run(conn, run_date, str(MEMORY_PATH))
    cutoff = (date.fromisoformat(run_date) - timedelta(days=lookback_days)).isoformat()

    checked = [dict(r) for r in conn.execute(
        """SELECT d.*, p.payload
           FROM investment_decisions d
           LEFT JOIN event_previews p ON p.event_uid = d.event_uid
           WHERE d.event_date BETWEEN ? AND ? AND d.run_date < ?
           ORDER BY d.event_date, d.ticker""",
        (cutoff, run_date, run_date),
    )]
    findings: list[dict] = []
    now = datetime.now(timezone.utc).isoformat()
    for d in checked:
        payload = parse_payload(d.get("payload"))
        hint = _outcome_hint(" ".join(str(payload.get(k, "")) for k in ("decision", "lean", "bull", "bear")))
        if hint == "positive" and d["action"] in ("PASS", "WATCH"):
            findings.append(_finding(run_id, d, "missed_opportunity", "medium",
                                     f"{d['ticker']} looked positive after a cautious decision.",
                                     "When a preview reports a strong beat plus raised outlook, raise score faster.",
                                     now))
        elif hint == "negative_or_bad_data" and d["action"] == "BUY":
            findings.append(_finding(run_id, d, "bad_decision", "high",
                                     f"{d['ticker']} had weak/bad-date language despite a BUY decision.",
                                     "Never allow BUY when preview contains wrong-date, unverified, miss, or lowered-outlook language.",
                                     now))

    missed = _missed_high_significance(conn, run_date, cutoff, run_id, now)
    findings.extend(missed)
    if findings:
        db.save_critic_findings(conn, findings)
        _update_memory(memory, findings)
        save_memory(memory)

    report_path = write_critic_report(run_date, checked, findings, memory)
    db.finish_critic_run(conn, run_id, decisions_checked=len(checked),
                         findings_count=len(findings), missed_count=len(missed),
                         report_path=str(report_path),
                         notes=["Outcome checks are heuristic unless price data is later attached."])
    conn.close()
    return {"run_id": run_id, "report_path": report_path, "findings": findings}


def collect_price_snapshots(run_date: str | None = None, decision_run_id: int | None = None,
                            limit: int = 50) -> dict:
    """Snapshot nfin/Nasdaq quote prices for latest BUY/WATCH decisions."""
    run_date = run_date or today_iso()
    conn = db.connect()
    db.init_db(conn)
    if decision_run_id is None:
        row = conn.execute("SELECT MAX(id) id FROM decision_agent_runs").fetchone()
        decision_run_id = row["id"] if row else None
    if not decision_run_id:
        conn.close()
        return {"snapshots": 0, "errors": ["no decision run found"]}

    decisions = [dict(r) for r in conn.execute(
        """SELECT id, ticker FROM investment_decisions
           WHERE run_id=? AND action IN ('BUY','WATCH')
           ORDER BY score DESC, ticker LIMIT ?""",
        (decision_run_id, limit),
    )]
    report = CollectorReport("nfin_quote_summary", 3, "api")
    http = HttpClient(report, rate_delay=0.15)
    created_at = datetime.now(timezone.utc).isoformat()
    snapshots = []
    for d in decisions:
        url = f"https://api.nfin.dev/v1/quote/{quote(d['ticker'])}/summary"
        payload = http.get_json(url, respect_robots=False)
        price = _price_from_quote(payload or {})
        snapshots.append({
            "decision_id": d["id"],
            "ticker": d["ticker"],
            "snapshot_date": run_date,
            "price": price,
            "price_source": "nfin_quote_summary",
            "raw_json": json.dumps(payload or {}, ensure_ascii=False),
            "created_at": created_at,
        })
    if snapshots:
        db.save_price_snapshots(conn, snapshots)
    conn.close()
    return {"snapshots": len(snapshots), "errors": report.errors + report.tos_issues}


def _price_from_quote(payload: dict) -> float | None:
    data = ((payload.get("data") or {}).get("data") or {})
    bidask = data.get("bidAsk") or {}
    values = []
    for key in ("Bid * Size", "Ask * Size"):
        raw = ((bidask.get(key) or {}).get("value") or "").split("*")[0].strip()
        val = _parse_price(raw)
        if val is not None:
            values.append(val)
    if values:
        return round(sum(values) / len(values), 4)
    summary = data.get("summaryData") or {}
    return _parse_price(((summary.get("PreviousClose") or {}).get("value") or ""))


def _parse_price(value: str) -> float | None:
    text = str(value or "").replace("$", "").replace(",", "").strip()
    try:
        return float(text)
    except Exception:
        return None


def _finding(run_id: int, decision: dict, kind: str, severity: str,
             summary: str, lesson: str, created_at: str) -> dict:
    return {
        "run_id": run_id,
        "event_uid": decision.get("event_uid"),
        "ticker": decision.get("ticker"),
        "finding_type": kind,
        "severity": severity,
        "summary": summary,
        "lesson": lesson,
        "created_at": created_at,
    }


def _missed_high_significance(conn, run_date: str, cutoff: str, run_id: int, now: str) -> list[dict]:
    rows = [dict(r) for r in conn.execute(
        """SELECT e.uid event_uid, e.event_date, p.ticker, p.payload
           FROM event_previews p JOIN events e ON e.uid = p.event_uid
           WHERE e.event_date BETWEEN ? AND ?
             AND e.uid NOT IN (SELECT event_uid FROM investment_decisions WHERE run_date <= ?)
           ORDER BY e.event_date, p.ticker""",
        (cutoff, run_date, run_date),
    )]
    out = []
    for r in rows:
        payload = parse_payload(r["payload"])
        sig = (payload.get("significance") or "").lower()
        if "high" not in sig:
            continue
        out.append({
            "run_id": run_id,
            "event_uid": r["event_uid"],
            "ticker": r["ticker"],
            "finding_type": "missed_tracking",
            "severity": "medium",
            "summary": f"{r['ticker']} was high-significance but had no prior decision record.",
            "lesson": "Keep the decision horizon wide enough to include high-significance upcoming reports.",
            "created_at": now,
        })
    return out[:50]


def _update_memory(memory: dict, findings: list[dict]):
    existing = {l.get("lesson") for l in memory.get("lessons", [])}
    for f in findings:
        lesson = f["lesson"]
        if lesson in existing:
            continue
        memory.setdefault("lessons", []).append({
            "date": today_iso(),
            "lesson": lesson,
            "source": f["finding_type"],
            "severity": f["severity"],
        })
        existing.add(lesson)
    memory["lessons"] = memory.get("lessons", [])[-50:]


def write_critic_report(run_date: str, checked: list[dict], findings: list[dict], memory: dict) -> Path:
    out_dir = REPORT_DIR / "critics"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{run_date}.md"
    lines = [
        f"# Critic Agent Report — {run_date}",
        "",
        "Systematic review of prior paper decisions, missed opportunities, and memory updates.",
        "",
        f"Decisions checked: {len(checked)}",
        f"Findings: {len(findings)}",
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("- No critic findings today.")
    for f in findings[:80]:
        lines += [
            f"- **{f['finding_type']} · {f['severity']} · {f.get('ticker') or 'n/a'}**",
            f"  - {f['summary']}",
            f"  - Lesson: {f['lesson']}",
        ]
    lines += ["", "## Current Memory Lessons"]
    for l in memory.get("lessons", [])[-15:]:
        lines.append(f"- {l.get('date')}: {l.get('lesson')}")
    path.write_text("\n".join(lines) + "\n")
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run decision or critic agent.")
    ap.add_argument("agent", choices=["decision", "critic"])
    ap.add_argument("--date", default=today_iso())
    ap.add_argument("--horizon-days", type=int, default=7)
    ap.add_argument("--lookback-days", type=int, default=14)
    args = ap.parse_args()
    if args.agent == "decision":
        result = run_decision_agent(args.date, args.horizon_days)
    else:
        result = run_critic_agent(args.date, args.lookback_days)
    print(f"Run #{result['run_id']} report: {result['report_path']}")
