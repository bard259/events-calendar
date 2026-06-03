"""Anthropic-centered ecosystem knowledge graph — chips · AI · space · energy.

A CURATED, typed relationship graph (reference knowledge, not event data) centered on
Anthropic and expanded outward through its investors, compute suppliers, the chip supply
chain beneath them, the energy/nuclear that powers the data centers, and the adjacent
space economy. Each edge has a TYPE (invests_in / supplies / powers / partners / customer /
contracts) and a short sourced note. Layout: cluster-separated force sim with Anthropic
pinned at the center. Exports app/assets/anthropic_graph.json.

Grounding (as of the project's Jun-2026 world): Amazon (~$33B) + Google (~$40B) +
Microsoft ($5B) + Nvidia ($10B) invest in Anthropic; AWS Trainium / Google TPU / Azure
supply compute (Broadcom & Marvell co-design those ASICs); TSMC fabs ~92% of AI chips with
SK Hynix/Micron/Samsung HBM and ASML/AMAT/Lam/KLA equipment; hyperscalers contract nuclear
(Constellation, Talen, Oklo, Kairos, X-energy, Vistra); SpaceX/Starlink uses STMicro/Wistron/
Filtronic and serves NASA/Space Force.  Refresh periodically.
"""
from __future__ import annotations

import json
import math
import random

from config import ROOT_DIR

GRAPH_JSON = ROOT_DIR / "app" / "assets" / "anthropic_graph.json"

SECTOR_COLORS = {
    "AI Labs": "#a855f7", "Cloud": "#3d8ef8", "Chips": "#38bdf8", "Memory": "#22d3ee",
    "Foundry & Equipment": "#818cf8", "Hardware": "#34d399", "Space": "#f472b6",
    "Energy": "#fb923c", "Investors": "#cbd5e1", "Government": "#94a3b8",
}
EDGE_COLORS = {
    "invests_in": "#34d399", "supplies": "#3d8ef8", "powers": "#fbbf24",
    "partners": "#a855f7", "customer": "#fb923c", "contracts": "#f87171",
}

# id | label | sector | ticker(None if private/gov) | kind
ENTITIES = [
    ("anthropic", "Anthropic", "AI Labs", None, "private"),
    ("openai", "OpenAI", "AI Labs", None, "private"),
    ("xai", "xAI", "AI Labs", None, "private"),
    ("mistral", "Mistral AI", "AI Labs", None, "private"),
    ("deepmind", "Google DeepMind", "AI Labs", None, "subsidiary"),
    # Cloud / hyperscalers
    ("AMZN", "Amazon (AWS)", "Cloud", "AMZN", "public"),
    ("GOOGL", "Alphabet (Google Cloud)", "Cloud", "GOOGL", "public"),
    ("MSFT", "Microsoft (Azure)", "Cloud", "MSFT", "public"),
    ("ORCL", "Oracle (OCI)", "Cloud", "ORCL", "public"),
    ("CRWV", "CoreWeave", "Cloud", "CRWV", "public"),
    ("META", "Meta", "Cloud", "META", "public"),
    # Chips — GPU / accelerator / custom silicon
    ("NVDA", "Nvidia", "Chips", "NVDA", "public"),
    ("AMD", "AMD", "Chips", "AMD", "public"),
    ("AVGO", "Broadcom", "Chips", "AVGO", "public"),
    ("MRVL", "Marvell", "Chips", "MRVL", "public"),
    ("ARM", "Arm Holdings", "Chips", "ARM", "public"),
    ("INTC", "Intel", "Chips", "INTC", "public"),
    ("QCOM", "Qualcomm", "Chips", "QCOM", "public"),
    ("STM", "STMicroelectronics", "Chips", "STM", "public"),
    # Foundry & equipment
    ("TSM", "TSMC", "Foundry & Equipment", "TSM", "public"),
    ("ASML", "ASML", "Foundry & Equipment", "ASML", "public"),
    ("AMAT", "Applied Materials", "Foundry & Equipment", "AMAT", "public"),
    ("LRCX", "Lam Research", "Foundry & Equipment", "LRCX", "public"),
    ("KLAC", "KLA", "Foundry & Equipment", "KLAC", "public"),
    # Memory (HBM)
    ("MU", "Micron", "Memory", "MU", "public"),
    ("hynix", "SK Hynix", "Memory", None, "public"),
    ("samsung", "Samsung", "Memory", None, "public"),
    # Hardware / networking / power-cooling
    ("SMCI", "Super Micro", "Hardware", "SMCI", "public"),
    ("DELL", "Dell", "Hardware", "DELL", "public"),
    ("ANET", "Arista", "Hardware", "ANET", "public"),
    ("VRT", "Vertiv", "Hardware", "VRT", "public"),
    ("ETN", "Eaton", "Hardware", "ETN", "public"),
    # Space
    ("spacex", "SpaceX / Starlink", "Space", None, "private"),
    ("RKLB", "Rocket Lab", "Space", "RKLB", "public"),
    ("wistron", "Wistron NeWeb", "Space", None, "public"),
    ("filtronic", "Filtronic", "Space", None, "public"),
    ("nasa", "NASA", "Government", None, "gov"),
    ("spaceforce", "US Space Force / DoD", "Government", None, "gov"),
    # Energy / nuclear / uranium
    ("CEG", "Constellation Energy", "Energy", "CEG", "public"),
    ("VST", "Vistra", "Energy", "VST", "public"),
    ("TLN", "Talen Energy", "Energy", "TLN", "public"),
    ("OKLO", "Oklo", "Energy", "OKLO", "public"),
    ("SMR", "NuScale Power", "Energy", "SMR", "public"),
    ("xenergy", "X-energy", "Energy", None, "private"),
    ("kairos", "Kairos Power", "Energy", None, "private"),
    ("terrapower", "TerraPower", "Energy", None, "private"),
    ("CCJ", "Cameco (uranium)", "Energy", "CCJ", "public"),
    # Investors / VC
    ("menlo", "Menlo Ventures", "Investors", None, "private"),
    ("lightspeed", "Lightspeed", "Investors", None, "private"),
    ("iconiq", "ICONIQ Growth", "Investors", None, "private"),
    ("CRM", "Salesforce Ventures", "Investors", "CRM", "public"),
]

# (source, target, type, note)  — source --type--> target
RELATIONS = [
    # ── Anthropic: investors ──
    ("AMZN", "anthropic", "invests_in", "~$8B + up to $25B (~$33B total)"),
    ("GOOGL", "anthropic", "invests_in", "up to $40B"),
    ("MSFT", "anthropic", "invests_in", "up to $5B"),
    ("NVDA", "anthropic", "invests_in", "up to $10B"),
    ("menlo", "anthropic", "invests_in", "lead VC"),
    ("lightspeed", "anthropic", "invests_in", ""),
    ("iconiq", "anthropic", "invests_in", ""),
    ("CRM", "anthropic", "invests_in", "Salesforce Ventures"),
    # ── Anthropic: compute suppliers / customers ──
    ("AMZN", "anthropic", "supplies", "AWS Trainium, up to 5GW; $100B AWS commitment"),
    ("GOOGL", "anthropic", "supplies", "Google Cloud TPU, multi-GW"),
    ("MSFT", "anthropic", "supplies", "Azure; $30B capacity commitment"),
    ("AVGO", "anthropic", "supplies", "co-designs next-gen TPU compute"),
    ("anthropic", "CRM", "customer", "Claude in Salesforce/enterprise"),
    # ── Cloud ← GPU/accelerator suppliers ──
    ("NVDA", "AMZN", "supplies", "GPUs"), ("NVDA", "GOOGL", "supplies", "GPUs"),
    ("NVDA", "MSFT", "supplies", "GPUs"), ("NVDA", "ORCL", "supplies", "GPUs"),
    ("NVDA", "CRWV", "supplies", "GPUs"), ("NVDA", "META", "supplies", "GPUs"),
    ("NVDA", "xai", "supplies", "Colossus GPUs"),
    ("AMD", "MSFT", "supplies", "MI-series"), ("AMD", "META", "supplies", "MI-series"),
    ("AMD", "ORCL", "supplies", "MI-series"), ("AMD", "openai", "supplies", "up to 6GW deal"),
    # ── Custom silicon co-design (ASIC) ──
    ("AVGO", "GOOGL", "supplies", "TPU ASIC co-design (~60% ASIC share)"),
    ("AVGO", "META", "supplies", "MTIA co-design"),
    ("AVGO", "openai", "supplies", "custom inference ASIC"),
    ("MRVL", "AMZN", "supplies", "Trainium custom silicon (~35% share)"),
    ("MRVL", "MSFT", "supplies", "Maia custom silicon"),
    ("NVDA", "MRVL", "invests_in", "$2B; NVLink Fusion"),
    # ── Foundry & equipment ──
    ("TSM", "NVDA", "supplies", "fabs ~92% of advanced AI chips"),
    ("TSM", "AMD", "supplies", "fab"), ("TSM", "AVGO", "supplies", "fab"),
    ("TSM", "MRVL", "supplies", "fab"), ("TSM", "GOOGL", "supplies", "TPU fab"),
    ("TSM", "AMZN", "supplies", "Trainium fab"), ("TSM", "MSFT", "supplies", "Maia fab"),
    ("ASML", "TSM", "supplies", "EUV lithography"), ("AMAT", "TSM", "supplies", "deposition/etch"),
    ("LRCX", "TSM", "supplies", "etch"), ("KLAC", "TSM", "supplies", "process control"),
    # ── Memory (HBM) ──
    ("hynix", "NVDA", "supplies", "HBM (~62% share)"), ("MU", "NVDA", "supplies", "HBM"),
    ("samsung", "NVDA", "supplies", "HBM"), ("hynix", "AMD", "supplies", "HBM"),
    ("MU", "AMD", "supplies", "HBM"),
    # ── Hardware / networking / power-cooling ──
    ("SMCI", "CRWV", "supplies", "AI servers"), ("SMCI", "MSFT", "supplies", "AI servers"),
    ("DELL", "AMZN", "supplies", "servers"), ("DELL", "xai", "supplies", "Colossus servers"),
    ("ANET", "MSFT", "supplies", "AI networking"), ("ANET", "META", "supplies", "AI networking"),
    ("VRT", "CRWV", "supplies", "power & cooling"), ("VRT", "MSFT", "supplies", "power & cooling"),
    ("ETN", "GOOGL", "supplies", "data-center electrical"),
    ("SMCI", "NVDA", "partners", "reference AI systems"),
    # ── Energy / nuclear powers the data centers ──
    ("CEG", "MSFT", "powers", "Three Mile Island restart, 835MW PPA"),
    ("TLN", "AMZN", "powers", "Susquehanna nuclear, 1.9GW"),
    ("AMZN", "xenergy", "invests_in", "$500M SMR round; ~5GW target"),
    ("GOOGL", "kairos", "partners", "500MW SMR development"),
    ("VST", "META", "powers", "nuclear PPA"), ("CEG", "META", "powers", "nuclear PPA"),
    ("OKLO", "META", "powers", "SMR commitment"), ("terrapower", "META", "partners", "SMR"),
    ("CCJ", "CEG", "supplies", "uranium fuel"), ("CCJ", "VST", "supplies", "uranium fuel"),
    ("CEG", "anthropic", "powers", "nuclear powers AWS/Azure AI capacity"),
    # ── AI labs (peers / OpenAI cluster) ──
    ("MSFT", "openai", "invests_in", "Azure partnership"),
    ("NVDA", "openai", "invests_in", "up to $100B"),
    ("MSFT", "openai", "supplies", "Azure compute"),
    ("ORCL", "openai", "supplies", "Stargate capacity"),
    ("deepmind", "GOOGL", "partners", "Gemini / Google subsidiary"),
    ("xai", "spacex", "partners", "Musk ecosystem; shared infra"),
    # ── Space ──
    ("STM", "spacex", "supplies", "Starlink silicon (decade partnership)"),
    ("wistron", "spacex", "supplies", "Starlink ground terminals"),
    ("filtronic", "spacex", "supplies", "RF / E-band modules"),
    ("spacex", "nasa", "supplies", "launch / Artemis (~$4B)"),
    ("spacex", "spaceforce", "contracts", "Starshield; missile-tracking sats"),
    ("RKLB", "nasa", "supplies", "small-launch / spacecraft"),
    ("spacex", "MSFT", "partners", "Starlink global internet"),
]


def _layout(nodes, sectors, edges, center="anthropic", iterations=600, seed=11):
    rnd = random.Random(seed)
    grps = sorted(set(sectors.values()))
    anchors = {}
    for i, g in enumerate(grps):
        ang = 2 * math.pi * i / max(1, len(grps))
        anchors[g] = (0.5 + 0.36 * math.cos(ang), 0.5 + 0.36 * math.sin(ang))
    pos = {n: [anchors[sectors[n]][0] + rnd.uniform(-0.03, 0.03),
               anchors[sectors[n]][1] + rnd.uniform(-0.03, 0.03)] for n in nodes}
    pos[center] = [0.5, 0.5]
    k = math.sqrt(1.0 / max(1, len(nodes)))
    t = 0.08
    for _ in range(iterations):
        disp = {n: [0.0, 0.0] for n in nodes}
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                a, b = nodes[i], nodes[j]
                dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
                d = math.hypot(dx, dy) or 0.001
                rep = (k * k) / d * (1.0 if sectors[a] == sectors[b] else 0.5)
                ux, uy = dx / d, dy / d
                disp[a][0] += ux * rep; disp[a][1] += uy * rep
                disp[b][0] -= ux * rep; disp[b][1] -= uy * rep
        for a, b in edges:
            dx, dy = pos[a][0] - pos[b][0], pos[a][1] - pos[b][1]
            d = math.hypot(dx, dy) or 0.001
            att = (d * d) / k
            ux, uy = dx / d, dy / d
            disp[a][0] -= ux * att; disp[a][1] -= uy * att
            disp[b][0] += ux * att; disp[b][1] += uy * att
        for n in nodes:
            ax, ay = anchors[sectors[n]]
            disp[n][0] += (ax - pos[n][0]) * 0.55
            disp[n][1] += (ay - pos[n][1]) * 0.55
        for n in nodes:
            if n == center:
                continue
            dd = disp[n]; dl = math.hypot(dd[0], dd[1]) or 0.001
            pos[n][0] += (dd[0] / dl) * min(dl, t)
            pos[n][1] += (dd[1] / dl) * min(dl, t)
        t = max(0.01, t * 0.99)
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    sx = (maxx - minx) or 1; sy = (maxy - miny) or 1
    return {n: [round((pos[n][0] - minx) / sx, 4), round((pos[n][1] - miny) / sy, 4)] for n in nodes}


def build() -> dict:
    sectors = {e[0]: e[2] for e in ENTITIES}
    labels = {e[0]: e[1] for e in ENTITIES}
    tickers = {e[0]: e[3] for e in ENTITIES}
    kinds = {e[0]: e[4] for e in ENTITIES}
    ids = [e[0] for e in ENTITIES]
    deg = {i: 0 for i in ids}
    for s, d, *_ in RELATIONS:
        deg[s] = deg.get(s, 0) + 1
        deg[d] = deg.get(d, 0) + 1
    pos = _layout(ids, sectors, [(s, d) for s, d, *_ in RELATIONS])
    nodes = [{
        "id": i, "label": labels[i], "sector": sectors[i], "ticker": tickers[i],
        "kind": kinds[i], "degree": deg.get(i, 0), "x": pos[i][0], "y": pos[i][1],
    } for i in ids]
    edges = [{"a": s, "b": d, "type": ty, "note": note} for s, d, ty, note in RELATIONS]
    payload = {"center": "anthropic", "nodes": nodes, "edges": edges,
               "sectorColors": SECTOR_COLORS, "edgeColors": EDGE_COLORS}
    GRAPH_JSON.parent.mkdir(parents=True, exist_ok=True)
    GRAPH_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


if __name__ == "__main__":
    p = build()
    from collections import Counter
    print(f"Anthropic ecosystem graph: {len(p['nodes'])} nodes, {len(p['edges'])} edges → {GRAPH_JSON}")
    print(f"  sectors: {dict(Counter(n['sector'] for n in p['nodes']))}")
    print(f"  edge types: {dict(Counter(e['type'] for e in p['edges']))}")
