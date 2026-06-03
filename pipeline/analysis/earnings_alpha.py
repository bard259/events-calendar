"""Continuously-learning earnings-alpha module.

Two forward outputs per upcoming earnings report:
  1. POP score (0–100) — likelihood of a *post-earnings increase*, from the same signals the
     decision agent trusts (asymmetry setup, AI-infra momentum, preview confidence/significance,
     positive-outlook language, mega-cap liquidity), minus risk/quality flags.
  2. LOOK-AHEAD days — how many trading days *before* the report to enter, grounded in the
     pre-earnings-announcement-drift literature (run-up is strongest when entered ~5–15 trading
     days out; the drift typically fades ~day 9). Stronger signal → enter earlier.

The loop LEARNS: `evaluate_outcomes` reads the daily price snapshots, computes the realized
pre→post-earnings return for events that have passed, stores them in `earnings_outcomes`, and
`learn` aggregates hit-rate / average drift by tier and nudges the thresholds and per-tier
look-ahead in `memory/earnings_alpha_params.json`. Over time the recommendations self-tune to
what actually paid off. Research, not advice.

Sources: pre-earnings-announcement-drift research (Easton/Gao/Gao SSRN 1786697; PrEA-momentum,
ScienceDirect S0165176520303177).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import db
from config import PIPELINE_DIR
from decision_agents import ai_infra_momentum_score, parse_payload

PARAMS_PATH = PIPELINE_DIR / "memory" / "earnings_alpha_params.json"

DEFAULT_PARAMS = {
    "version": 1,
    "updated_at": "",
    # Research-grounded defaults (trading days before earnings to enter), refined by learning.
    "tier_lookahead": {"high": 12, "medium": 7, "low": 2},
    "thresholds": {"high": 62, "medium": 40},
    "weights": {
        "setup_high": 30, "setup_notable": 16, "ai_infra": 16, "positive_outlook": 14,
        "confidence_high": 16, "confidence_medium": 8, "significance_high": 12,
        "megacap": 6, "risk_flag": -12,
    },
    "learned": {"samples": 0, "hit_rate": None, "avg_drift_pct": None, "by_tier": {}},
}

_POSITIVE = ["raises", "stronger outlook", "turnaround looks real", "beat", "raised",
             "record", "accelerat", "above consensus", "beat-and-raise"]
_RISK = ["miss", "weak outlook", "lowered", "two-sided", "sell-the-news", "near highs",
         "already reported", "unverified", "wrong", "do not rely"]


def load_params(path: Path = PARAMS_PATH) -> dict:
    try:
        p = json.loads(path.read_text())
        # backfill any new default keys
        for k, v in DEFAULT_PARAMS.items():
            p.setdefault(k, v)
        return p
    except Exception:
        save_params(DEFAULT_PARAMS.copy(), path)
        return json.loads(json.dumps(DEFAULT_PARAMS))


def save_params(params: dict, path: Path = PARAMS_PATH):
    params["updated_at"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(params, ensure_ascii=False, indent=2))


def _has(text: str, terms: list[str]) -> bool:
    t = text.lower()
    return any(term in t for term in terms)


def _market_cap(row: dict) -> float:
    try:
        nf = (json.loads(row.get("raw_json") or "{}").get("nfin_row") or {})
    except Exception:
        nf = {}
    s = str(nf.get("marketCap") or "").replace("$", "").replace(",", "").strip()
    mult = 1.0
    if s[-1:].upper() == "T":
        mult, s = 1e12, s[:-1]
    elif s[-1:].upper() == "B":
        mult, s = 1e9, s[:-1]
    elif s[-1:].upper() == "M":
        mult, s = 1e6, s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return 0.0


def _tier(score: int, params: dict) -> str:
    th = params["thresholds"]
    return "high" if score >= th["high"] else "medium" if score >= th["medium"] else "low"


def assess(row: dict, params: dict) -> dict:
    payload = parse_payload(row.get("payload"))
    text = " ".join(str(payload.get(k, "")) for k in (
        "decision", "confidence", "significance", "lean", "bull", "bear", "watch", "bar", "as_of"))
    w = params["weights"]
    score, rationale = 0, []

    setup_score = row.get("setup_score") or 0
    if setup_score >= 70:
        score += w["setup_high"]; rationale.append(f"high-asymmetry setup ({setup_score})")
    elif setup_score >= 45:
        score += w["setup_notable"]; rationale.append(f"notable setup ({setup_score})")

    conf = (payload.get("confidence") or "").lower()
    if "high" in conf:
        score += w["confidence_high"]; rationale.append("high preview confidence")
    elif "medium" in conf:
        score += w["confidence_medium"]
    if "high" in (payload.get("significance") or "").lower():
        score += w["significance_high"]; rationale.append("high significance")

    if _has(text, _POSITIVE):
        score += w["positive_outlook"]; rationale.append("positive-outlook language")
    if ai_infra_momentum_score(row.get("ticker", ""), text) >= 3:
        score += w["ai_infra"]; rationale.append("AI-infrastructure momentum")
    if _market_cap(row) >= 200e9:
        score += w["megacap"]; rationale.append("mega-cap liquidity")
    if _has(text, _RISK):
        score += w["risk_flag"]; rationale.append("offsetting risk / quality flag")

    score = max(0, min(100, int(score)))
    tier = _tier(score, params)
    lookahead = int(params["tier_lookahead"][tier])
    likelihood = {"high": "elevated", "medium": "moderate", "low": "low"}[tier]
    return {
        "event_uid": row["uid"], "ticker": row.get("ticker"), "event_date": row.get("event_date"),
        "pop_score": score, "increase_likelihood": likelihood, "lookahead_days": lookahead,
        "hold_through": "Hold through the report; pre-earnings drift typically fades ~9 trading days in.",
        "rationale": json.dumps(rationale), "params_version": params.get("version", 1),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def enrich_and_save(conn) -> int:
    """Compute alpha predictions for every earnings event that has a preview."""
    db.init_db(conn)
    params = load_params()
    rows = [dict(r) for r in conn.execute(
        """SELECT e.uid, e.event_date, e.raw_json, p.ticker, p.payload, s.score AS setup_score
           FROM event_previews p
           JOIN events e ON e.uid = p.event_uid
           LEFT JOIN event_setups s ON s.event_uid = e.uid""")]
    predictions = [assess(r, params) for r in rows]
    conn.execute("DELETE FROM earnings_alpha")
    conn.commit()
    if predictions:
        db.save_earnings_alpha(conn, predictions)
    return len(predictions)


def evaluate_outcomes(conn) -> int:
    """Compute realized pre→post-earnings returns from daily price snapshots."""
    db.init_db(conn)
    snaps: dict[str, list[tuple[str, float]]] = {}
    try:
        cur = conn.execute(
            "SELECT ticker, snapshot_date, price FROM investment_price_snapshots "
            "WHERE price IS NOT NULL ORDER BY snapshot_date")
    except Exception:
        return 0  # no snapshots accumulated yet (loop builds outcomes over time)
    for r in cur:
        snaps.setdefault(r["ticker"], []).append((r["snapshot_date"], r["price"]))

    events = [dict(r) for r in conn.execute(
        "SELECT event_uid, ticker, event_date, pop_score FROM earnings_alpha")]
    now = datetime.now(timezone.utc).isoformat()
    out = []
    for ev in events:
        series = snaps.get(ev["ticker"]) or []
        pre = [s for s in series if s[0] <= ev["event_date"]]
        post = [s for s in series if s[0] > ev["event_date"]]
        if not pre or not post:
            continue
        pre_date, pre_price = pre[-1]
        post_date, post_price = post[0]
        if not pre_price:
            continue
        ret = round((post_price - pre_price) / pre_price * 100, 3)
        out.append({
            "event_uid": ev["event_uid"], "ticker": ev["ticker"], "event_date": ev["event_date"],
            "pre_date": pre_date, "pre_price": pre_price, "post_date": post_date,
            "post_price": post_price, "ret_pct": ret, "increased": 1 if ret > 0 else 0,
            "pop_score": ev["pop_score"], "evaluated_at": now,
        })
    if out:
        db.save_earnings_outcomes(conn, out)
    return len(out)


def learn(conn, params: dict | None = None) -> dict:
    """Aggregate realized outcomes and self-tune thresholds + per-tier look-ahead."""
    params = params or load_params()
    rows = [dict(r) for r in conn.execute(
        "SELECT ret_pct, increased, pop_score FROM earnings_outcomes")]
    if not rows:
        return params  # nothing learned yet — keep research defaults

    n = len(rows)
    hit_rate = round(sum(r["increased"] for r in rows) / n, 3)
    avg_drift = round(sum(r["ret_pct"] for r in rows) / n, 3)
    by_tier: dict[str, dict] = {}
    for tier in ("high", "medium", "low"):
        bucket = [r for r in rows if _tier(r["pop_score"], params) == tier]
        if not bucket:
            continue
        b_hit = round(sum(r["increased"] for r in bucket) / len(bucket), 3)
        b_ret = round(sum(r["ret_pct"] for r in bucket) / len(bucket), 3)
        by_tier[tier] = {"samples": len(bucket), "hit_rate": b_hit, "avg_ret_pct": b_ret}
        # Adaptive look-ahead: strong realized drift → enter a touch earlier; weak/negative → later/less.
        cur = params["tier_lookahead"][tier]
        if len(bucket) >= 8:
            if b_ret > 3 and b_hit >= 0.6:
                params["tier_lookahead"][tier] = min(15, cur + 1)
            elif b_ret < 0 or b_hit < 0.45:
                params["tier_lookahead"][tier] = max(1, cur - 1)

    params["learned"] = {"samples": n, "hit_rate": hit_rate, "avg_drift_pct": avg_drift,
                         "by_tier": by_tier, "updated_at": datetime.now(timezone.utc).isoformat()}
    save_params(params)
    return params


def run_learning(conn) -> dict:
    """Daily learning step: evaluate realized outcomes, then self-tune params."""
    evaluated = evaluate_outcomes(conn)
    params = learn(conn)
    return {"outcomes_evaluated": evaluated,
            "samples": params.get("learned", {}).get("samples", 0),
            "hit_rate": params.get("learned", {}).get("hit_rate")}


if __name__ == "__main__":
    conn = db.connect()
    n = enrich_and_save(conn)
    res = run_learning(conn)
    conn.close()
    print(f"earnings-alpha predictions: {n}")
    print(f"learning: {res}")
