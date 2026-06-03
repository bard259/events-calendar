"""Build a company-relationship knowledge graph and precompute its layout.

NODES are companies (tickers that have a company card). An EDGE links two companies that
**co-move in the same event** — i.e. both appear in that event's stock-impact set (e.g. an
Anthropic event impacts NVDA/AMZN/GOOGL/MSFT; a defense event impacts LMT/RTX/NOC). Edge
weight = number of shared events. Sector ETFs are excluded (they aren't companies / company
cards). Isolated companies (no co-move edge) are dropped, so the graph shows the real
thematic clusters (AI compute, defense, energy, big-tech).

Layout is a stdlib **Fruchterman–Reingold** force-directed simulation (the standard for
relationship graphs), precomputed here so the app just plots x,y — no runtime physics and no
new app dependencies. Output: app/assets/company_graph.json.
"""
from __future__ import annotations

import argparse
import json
import math
import random

import db
from config import ROOT_DIR

GRAPH_JSON = ROOT_DIR / "app" / "assets" / "company_graph.json"

# Coarse sector groups (color buckets). Ticker overrides first (the connected ecosystem is
# mostly well-known names), then an industry-keyword fallback.
GROUP_COLORS = {
    "Semiconductors":      "#38bdf8",
    "Software & Cloud":    "#a855f7",
    "Internet & Media":    "#f472b6",
    "Hardware & Networking": "#22d3ee",
    "Defense & Aerospace": "#f87171",
    "Energy":              "#fbbf24",
    "Financials":          "#34d399",
    "Healthcare":          "#818cf8",
    "Consumer":            "#fb923c",
    "Other":               "#8fa3bf",
}

GROUP_BY_TICKER = {
    "NVDA": "Semiconductors", "AMD": "Semiconductors", "AVGO": "Semiconductors",
    "MU": "Semiconductors", "TSM": "Semiconductors", "INTC": "Semiconductors",
    "QCOM": "Semiconductors", "MRVL": "Semiconductors", "ARM": "Semiconductors",
    "AMAT": "Semiconductors", "LRCX": "Semiconductors", "KLAC": "Semiconductors",
    "ASML": "Semiconductors", "ALAB": "Semiconductors", "CRDO": "Semiconductors",
    "MSFT": "Software & Cloud", "ORCL": "Software & Cloud", "CRM": "Software & Cloud",
    "PLTR": "Software & Cloud", "SNOW": "Software & Cloud", "NOW": "Software & Cloud",
    "ADBE": "Software & Cloud", "PANW": "Software & Cloud", "CRWV": "Software & Cloud",
    "GOOGL": "Internet & Media", "META": "Internet & Media", "AMZN": "Internet & Media",
    "AAPL": "Hardware & Networking", "DELL": "Hardware & Networking", "HPE": "Hardware & Networking",
    "SMCI": "Hardware & Networking", "ANET": "Hardware & Networking", "CSCO": "Hardware & Networking",
    "VRT": "Hardware & Networking", "ETN": "Hardware & Networking",
    "LMT": "Defense & Aerospace", "RTX": "Defense & Aerospace", "NOC": "Defense & Aerospace",
    "BA": "Defense & Aerospace", "RKLB": "Defense & Aerospace",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "BP": "Energy",
    "JPM": "Financials", "GS": "Financials", "BAC": "Financials", "C": "Financials", "WFC": "Financials", "BLK": "Financials",
    "JNJ": "Healthcare", "MRK": "Healthcare", "PFE": "Healthcare", "ABBV": "Healthcare", "LLY": "Healthcare",
    "NKE": "Consumer", "COST": "Consumer", "WMT": "Consumer", "VSXY": "Consumer", "CTRN": "Consumer",
    "CAL": "Consumer", "KSS": "Consumer", "M": "Consumer", "TSLA": "Consumer", "F": "Consumer", "GM": "Consumer",
}

_IND_KEYWORDS = [
    ("Semiconductors", ["semiconductor", "chips"]),
    ("Software & Cloud", ["software", "computer programming", "data processing"]),
    ("Defense & Aerospace", ["aircraft", "guided missiles", "defense", "aerospace", "search & navigation"]),
    ("Energy", ["petroleum", "oil", "natural gas", "energy", "drilling"]),
    ("Financials", ["bank", "insurance", "finance", "investment", "securities"]),
    ("Healthcare", ["pharmaceutical", "medical", "health", "biological", "surgical"]),
    ("Consumer", ["retail", "apparel", "footwear", "stores", "restaurants", "beverage", "food"]),
    ("Hardware & Networking", ["communications equipment", "electronic", "computer", "telephone"]),
]


def _group(ticker: str, industry: str) -> str:
    if ticker in GROUP_BY_TICKER:
        return GROUP_BY_TICKER[ticker]
    ind = (industry or "").lower()
    for grp, kws in _IND_KEYWORDS:
        if any(k in ind for k in kws):
            return grp
    return "Other"


def _build_edges(conn, companies: set[str]):
    """Co-occurrence edges from event_stock_impacts (company tickers sharing an event)."""
    per_event: dict[str, set[str]] = {}
    for r in conn.execute("SELECT event_uid, ticker FROM event_stock_impacts"):
        if r["ticker"] in companies:
            per_event.setdefault(r["event_uid"], set()).add(r["ticker"])
    weights: dict[tuple[str, str], int] = {}
    for tickers in per_event.values():
        ts = sorted(tickers)
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                weights[(ts[i], ts[j])] = weights.get((ts[i], ts[j]), 0) + 1
    return weights


def _fruchterman_reingold(nodes: list[str], edges: dict, iterations=400, seed=7):
    rnd = random.Random(seed)
    pos = {n: [rnd.uniform(0, 1), rnd.uniform(0, 1)] for n in nodes}
    n = max(1, len(nodes))
    k = math.sqrt(1.0 / n)            # ideal edge length on a unit square
    t = 0.1                            # initial temperature
    adj = [(a, b, w) for (a, b), w in edges.items()]
    for _ in range(iterations):
        disp = {nd: [0.0, 0.0] for nd in nodes}
        # repulsion (all pairs)
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                dist = math.hypot(dx, dy) or 0.001
                force = (k * k) / dist
                ux, uy = dx / dist, dy / dist
                disp[a][0] += ux * force; disp[a][1] += uy * force
                disp[b][0] -= ux * force; disp[b][1] -= uy * force
        # attraction (edges, weighted)
        for a, b, w in adj:
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            dist = math.hypot(dx, dy) or 0.001
            force = (dist * dist) / k * (1 + 0.15 * (w - 1))
            ux, uy = dx / dist, dy / dist
            disp[a][0] -= ux * force; disp[a][1] -= uy * force
            disp[b][0] += ux * force; disp[b][1] += uy * force
        # integrate with temperature cap
        for nd in nodes:
            d = disp[nd]
            dl = math.hypot(d[0], d[1]) or 0.001
            pos[nd][0] += (d[0] / dl) * min(dl, t)
            pos[nd][1] += (d[1] / dl) * min(dl, t)
        t = max(0.01, t * 0.985)      # cool down
    # normalize to [0,1]
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    sx = (maxx - minx) or 1; sy = (maxy - miny) or 1
    for nd in nodes:
        pos[nd][0] = round((pos[nd][0] - minx) / sx, 4)
        pos[nd][1] = round((pos[nd][1] - miny) / sy, 4)
    return pos


def build(max_nodes: int = 90) -> dict:
    conn = db.connect()
    db.init_db(conn)
    cards = {r["ticker"]: dict(r) for r in conn.execute(
        "SELECT ticker, name, industry FROM company_cards")}
    companies = set(cards)

    weights = _build_edges(conn, companies)
    degree: dict[str, int] = {}
    for (a, b), w in weights.items():
        degree[a] = degree.get(a, 0) + 1
        degree[b] = degree.get(b, 0) + 1

    # keep the most-connected nodes; drop isolates
    keep = sorted(degree, key=lambda t: -degree[t])[:max_nodes]
    keepset = set(keep)
    edges = [{"a": a, "b": b, "weight": w} for (a, b), w in weights.items()
             if a in keepset and b in keepset]
    # event counts per company (node size)
    ev_count = {r["ticker"]: r["n"] for r in conn.execute(
        "SELECT ticker, COUNT(*) n FROM event_stock_impacts GROUP BY ticker")}

    pos = _fruchterman_reingold(keep, {(e["a"], e["b"]): e["weight"] for e in edges})
    nodes = []
    for t in keep:
        c = cards.get(t, {})
        nodes.append({
            "ticker": t, "name": c.get("name") or t,
            "group": _group(t, c.get("industry") or ""),
            "degree": degree.get(t, 0), "events": ev_count.get(t, 0),
            "x": pos[t][0], "y": pos[t][1],
        })
    conn.close()

    payload = {"nodes": nodes, "edges": edges, "groups": GROUP_COLORS}
    GRAPH_JSON.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


def main():
    ap = argparse.ArgumentParser(description="Build the company-relationship knowledge graph.")
    ap.add_argument("--max-nodes", type=int, default=90)
    args = ap.parse_args()
    p = build(args.max_nodes)
    from collections import Counter
    grp = Counter(n["group"] for n in p["nodes"])
    print(f"Graph: {len(p['nodes'])} nodes, {len(p['edges'])} edges → {GRAPH_JSON}")
    print(f"  groups: {dict(grp)}")


if __name__ == "__main__":
    main()
