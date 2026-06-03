"""Build per-company "company cards" — a separate entity from event cards.

A company card aggregates every event for a ticker and carries a plain-English intro:
  1. curated business/mission TL;DR (company_tldr.COMPANY_TLDR), else
  2. SEC industry (SIC description) → "{name} ({ticker}) — {industry}.", fetched from EDGAR
     and cached, else
  3. a clean "{name} ({ticker}) — {size}-cap company." fallback.

SEC lookups are capped per run and cached (memory/sic_cache.json, memory/sec_company_tickers.json),
so coverage of the long-tail earnings calendar fills in over repeated runs without hammering
EDGAR. Writes the `company_cards` table and app/assets/company_cards.json; the app links each
event card to its company card by ticker (ev.company_ticker).
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

import db
from config import PIPELINE_DIR, ROOT_DIR
from company_tldr import COMPANY_TLDR
from analysis.setup_signals import primary_ticker
from http_client import HttpClient
from models import CollectorReport

SIC_CACHE = PIPELINE_DIR / "memory" / "sic_cache.json"
CIK_CACHE = PIPELINE_DIR / "memory" / "sec_company_tickers.json"
CARDS_JSON = ROOT_DIR / "app" / "assets" / "company_cards.json"
COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"


def _load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


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


def _size_label(v: float) -> str:
    if v >= 200e9:
        return "mega"
    if v >= 10e9:
        return "large"
    if v >= 2e9:
        return "mid"
    if v > 0:
        return "small"
    return ""


def _clean_industry(sic_desc: str) -> str:
    s = (sic_desc or "").strip()
    if not s:
        return ""
    s = re.sub(r"^services-", "", s, flags=re.I)
    return s.lower()


def _resolve(ev: dict):
    """(ticker, name, market_cap_str) for an event, via nfin symbol or entity → ticker."""
    try:
        raw = json.loads(ev.get("raw_json") or "{}")
    except Exception:
        raw = {}
    nf = raw.get("nfin_row") or {}
    sym = str(nf.get("symbol") or "").strip().upper()
    if sym:
        return sym, str(nf.get("name") or ev.get("entity") or "").strip(), nf.get("marketCap")
    ent = ev.get("entity") or ""
    return (primary_ticker(ent).upper() if ent else ""), ent, None


def _cik_map(http) -> dict:
    cached = _load_json(CIK_CACHE, None)
    if cached:
        return cached
    data = http.get_json(COMPANY_TICKERS_URL, respect_robots=False) or {}
    m = {}
    for row in (data.values() if isinstance(data, dict) else []):
        t = str(row.get("ticker") or "").upper()
        if t:
            m[t] = {"cik": row.get("cik_str"), "title": row.get("title")}
    if m:
        _save_json(CIK_CACHE, m)
    return m


def build(sec_lookup_cap: int = 200) -> list[dict]:
    conn = db.connect()
    db.init_db(conn)
    rows = [dict(r) for r in conn.execute(
        "SELECT uid, entity, event_date, raw_json FROM events")]

    agg: dict[str, dict] = {}
    for ev in rows:
        ticker, name, mc = _resolve(ev)
        if not ticker:
            continue
        a = agg.setdefault(ticker, {"name": name or ticker, "market_cap": 0.0,
                                    "uids": [], "dates": []})
        if name and (not a["name"] or a["name"] == ticker):
            a["name"] = name
        v = _market_cap_value(mc)
        if v > a["market_cap"]:
            a["market_cap"] = v
        a["uids"].append(ev["uid"])
        a["dates"].append(ev["event_date"])

    # SEC industry enrichment — capped + cached, biggest market caps first (most visible).
    sic_cache = _load_json(SIC_CACHE, {})
    need = [t for t in agg if t not in COMPANY_TLDR and t not in sic_cache]
    need.sort(key=lambda t: -agg[t]["market_cap"])
    if need:
        report = CollectorReport("sec_company_facts", 3, "api")
        http = HttpClient(report, rate_delay=0.2)
        cikmap = _cik_map(http)
        for t in need[:sec_lookup_cap]:
            cik = (cikmap.get(t) or {}).get("cik")
            if not cik:
                sic_cache[t] = ""          # mark attempted (likely foreign/no EDGAR)
                continue
            data = http.get_json(SUBMISSIONS_URL.format(cik=int(cik)), respect_robots=False) or {}
            sic_cache[t] = data.get("sicDescription") or ""
        _save_json(SIC_CACHE, sic_cache)

    now = datetime.now(timezone.utc).isoformat()
    cards: list[dict] = []
    for t, a in agg.items():
        size = _size_label(a["market_cap"])
        name = a["name"]
        if t in COMPANY_TLDR:
            intro, src, industry = COMPANY_TLDR[t], "curated", ""
        else:
            industry = _clean_industry(sic_cache.get(t, ""))
            if industry:
                intro, src = f"{name} ({t}) — {industry}.", "sic"
            elif size:
                intro, src = f"{name} ({t}) — {size}-cap company.", "size"
            else:
                intro, src = f"{name} ({t}) — public company.", "size"
        dates = sorted(d for d in a["dates"] if d)
        cards.append({
            "ticker": t, "name": name, "intro": intro, "intro_source": src,
            "industry": industry, "size": size, "market_cap": a["market_cap"],
            "n_events": len(a["uids"]), "next_event": dates[0] if dates else None,
            "event_uids": json.dumps(a["uids"]), "updated_at": now,
        })

    db.save_company_cards(conn, cards)
    conn.close()
    _export(cards)
    return cards


def _export(cards: list[dict]):
    payload = {c["ticker"]: {
        "ticker": c["ticker"], "name": c["name"], "intro": c["intro"],
        "intro_source": c["intro_source"], "industry": c["industry"], "size": c["size"],
        "n_events": c["n_events"], "next_event": c["next_event"],
    } for c in cards}
    _save_json(CARDS_JSON, payload)


def main():
    ap = argparse.ArgumentParser(description="Build company cards (intro per ticker) + export.")
    ap.add_argument("--sec-cap", type=int, default=200,
                    help="Max new SEC industry lookups this run (cached across runs).")
    args = ap.parse_args()
    cards = build(args.sec_cap)
    by_src = {}
    for c in cards:
        by_src[c["intro_source"]] = by_src.get(c["intro_source"], 0) + 1
    print(f"Built {len(cards)} company cards → {CARDS_JSON}")
    print(f"  intro sources: {by_src}")


if __name__ == "__main__":
    main()
