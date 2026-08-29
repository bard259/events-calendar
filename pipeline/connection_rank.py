"""Measure how connected each company is to Nvidia, SpaceX, and Anthropic — and rank.

MEASUREMENT (a truncated weighted diffusion / Katz-style proximity):
  Build ONE undirected weighted relationship graph from
    (a) the curated Anthropic ecosystem map (`anthropic_graph.json`) — typed deal edges that
        include the private hubs SpaceX & Anthropic, and
    (b) the DB `stock_graph_edges` — public ticker↔ticker links (supplier/customer/partner/
        SEC-mention/same-industry/shared-event).
  Each edge gets a strength by relationship TYPE (a real supply/investment tie counts far more
  than a co-moved share price). From each hub we diffuse influence outward up to 3 hops with a
  0.5 per-hop decay and sum every decayed weighted path into a per-company `connection_score`.
  → rewards companies with *many, strong, short* links to the hub.

For each hub we rank the public companies by score and annotate each with its **next earnings
call date** (soonest cat-3 earnings in the DB) and the strongest connecting relationship.
Outputs: `app/assets/connection_rankings.json`, a markdown report under `pipeline/reports/
research/`, and prints the top rankings. Reference analytics over sourced graph data — not advice.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timezone

import db
from config import ROOT_DIR, PIPELINE_DIR

ANTHRO_JSON = ROOT_DIR / "app" / "assets" / "anthropic_graph.json"
OUT_JSON = ROOT_DIR / "app" / "assets" / "connection_rankings.json"
REPORT_DIR = PIPELINE_DIR / "reports" / "research"

HUBS = [("NVDA", "Nvidia"), ("spacex", "SpaceX"), ("anthropic", "Anthropic")]
MAX_HOPS = 3
DECAY = 0.5

REL_WEIGHTS = {
    "invests_in": 1.0, "co_design": 0.95, "supplies": 0.9, "supplier": 0.9, "customer": 0.9,
    "partners": 0.8, "partner": 0.8, "powers": 0.7, "contracts": 0.7,
    "sec_mention": 0.45, "same_industry": 0.25, "shared_event": 0.3,
}
def _w(rel: str) -> float:
    return REL_WEIGHTS.get((rel or "").lower(), 0.4)


def _load_graph(conn):
    """adj[u] = list[(v, weight, rel, note)]; names{id->label}; tickers set of public ids."""
    adj: dict[str, list] = defaultdict(list)
    names: dict[str, str] = {}
    public: set[str] = set()

    def add(a, b, w, rel, note):
        adj[a].append((b, w, rel, note))
        adj[b].append((a, w, rel, note))

    # (a) curated ecosystem (has private hubs spacex/anthropic + public tickers)
    try:
        eco = json.loads(ANTHRO_JSON.read_text())
        for n in eco.get("nodes", []):
            names[n["id"]] = n.get("label") or n["id"]
            if n.get("ticker"):
                public.add(n["id"])
        for e in eco.get("edges", []):
            add(e["a"], e["b"], _w(e.get("type")), e.get("type"), e.get("note") or "")
    except Exception as ex:
        print("ecosystem graph load skipped:", ex)

    # (b) DB stock graph (public ticker↔ticker)
    for r in conn.execute(
        "SELECT source_ticker, target_ticker, relationship, reason FROM stock_graph_edges"):
        a, b = r["source_ticker"], r["target_ticker"]
        public.add(a); public.add(b)
        add(a, b, _w(r["relationship"]), r["relationship"], r["reason"] or "")
    for r in conn.execute("SELECT ticker, name FROM stock_graph_nodes"):
        names.setdefault(r["ticker"], r["name"] or r["ticker"])
        public.add(r["ticker"])
    return adj, names, public


def _next_earnings(conn) -> dict:
    """ticker -> soonest cat-3 earnings date in the DB (high-confidence company match)."""
    out: dict[str, str] = {}
    for r in conn.execute(
        """SELECT i.ticker t, MIN(e.event_date) d
           FROM event_stock_impacts i JOIN events e ON e.uid = i.event_uid
           WHERE e.category_id = 3 AND lower(i.confidence) = 'high'
             AND (e.title LIKE '%earnings%' OR e.source = 'nfin_earnings_calendar')
           GROUP BY i.ticker"""):
        if r["d"]:
            out[r["t"]] = r["d"]
    return out


def _diffuse(adj, hub):
    """Truncated weighted diffusion from hub → {node: connection_score}."""
    score = defaultdict(float)
    frontier = {hub: 1.0}
    for _ in range(MAX_HOPS):
        nxt = defaultdict(float)
        for u, s in frontier.items():
            for v, w, *_ in adj.get(u, []):
                c = s * w * DECAY
                if c < 1e-4:
                    continue
                nxt[v] += c
        for v, c in nxt.items():
            if v != hub:
                score[v] += c
        frontier = nxt
    return score


def _best_link(adj, hub, node, names):
    """Short human explanation of node's strongest connection to hub."""
    # direct edge?
    best = None
    for v, w, rel, note in adj.get(node, []):
        if v == hub and (best is None or w > best[0]):
            best = (w, f"{rel.replace('_',' ')}" + (f" — {note}" if note else ""))
    if best:
        return "direct: " + best[1]
    # best 2-hop via M
    hub_nbrs = {v: (w, rel) for v, w, rel, _ in adj.get(hub, [])}
    best2 = None
    for v, w, rel, _ in adj.get(node, []):
        if v in hub_nbrs:
            score = w * hub_nbrs[v][0]
            if best2 is None or score > best2[0]:
                best2 = (score, f"via {names.get(v, v)} ({hub_nbrs[v][1].replace('_',' ')} / {rel.replace('_',' ')})")
    return best2[1] if best2 else "multi-hop"


def build(top_n: int = 20) -> dict:
    conn = db.connect(); db.init_db(conn)
    adj, names, public = _load_graph(conn)
    nxt = _next_earnings(conn)
    today = date.today().isoformat()

    hubs_out = []
    for hub_id, disp in HUBS:
        score = _diffuse(adj, hub_id)
        ranked = []
        for node, sc in score.items():
            if node not in public or node == hub_id:
                continue
            ranked.append({
                "ticker": node, "name": names.get(node, node), "score": round(sc, 4),
                "next_earnings": nxt.get(node), "link": _best_link(adj, hub_id, node, names),
            })
        ranked.sort(key=lambda r: (-r["score"], r["ticker"]))
        hubs_out.append({"hub": hub_id, "display": disp, "ranked": ranked[:top_n],
                         "n_connected": len(ranked)})
    conn.close()

    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), "as_of": today,
               "method": "weighted 3-hop diffusion (0.5/hop) over curated ecosystem + stock graph",
               "hubs": hubs_out}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    _write_report(payload)
    return payload


def _write_report(p: dict):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"connection_rankings_{p['as_of']}.md"
    lines = [f"# Connection rankings — Nvidia · SpaceX · Anthropic ({p['as_of']})", "",
             f"Method: {p['method']}. Score = summed decayed weighted relationship paths from the hub.",
             "Each company is annotated with its next earnings call date (from the DB) + strongest link.", ""]
    for h in p["hubs"]:
        lines += [f"## Most connected to {h['display']}  ({h['n_connected']} connected companies)", "",
                  "| # | Ticker | Company | Score | Next earnings | Strongest link |",
                  "|--:|--------|---------|------:|---------------|----------------|"]
        for i, r in enumerate(h["ranked"], 1):
            lines.append(f"| {i} | **{r['ticker']}** | {r['name'][:28]} | {r['score']} | "
                         f"{r['next_earnings'] or '—'} | {r['link'][:60]} |")
        lines.append("")
    path.write_text("\n".join(lines) + "\n")
    return path


def main():
    p = build()
    for h in p["hubs"]:
        print(f"\n=== Top connections to {h['display']} ({h['n_connected']} connected) ===")
        for i, r in enumerate(h["ranked"][:15], 1):
            print(f"  {i:2}. {r['ticker']:6} {r['score']:6.3f}  earn {r['next_earnings'] or '—':10}  "
                  f"{r['name'][:24]:24} | {r['link'][:46]}")
    print(f"\n→ {OUT_JSON}")


if __name__ == "__main__":
    main()
