"""Rules-based stock impact analysis.

Methodology
-----------
For each event we apply three layers of rules, in priority order:

  1. ENTITY MATCH — if the event entity/title contains a known company name, emit a
     high-confidence direct impact on that company's stock.

  2. KEYWORD / TITLE MATCH — scan title + description for financial keywords and emit
     sector or ETF impacts with directional reasoning.

  3. CATEGORY DEFAULT — every category has baseline sector impacts regardless of content.

Each impact record:
  { ticker, direction (+1/-1/0), confidence, reason, sector }

Direction semantics
  +1  positive expected impact (price tends to rise on this event type)
  -1  negative expected impact
   0  high-volatility / direction ambiguous; watch closely

Design principles
  - Pure Python stdlib, no ML, no API keys, no network calls.
  - Over-inclusive rather than under-inclusive: a trader reviewing the calendar can
    dismiss an irrelevant ticker; they cannot recover a missed one.
  - Confidence = "high" (direct company event) / "medium" (strong indirect link) /
    "low" (sector theme, speculative).
  - TL;DR reason ≤ 120 characters.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ── Entity → ticker lookup ─────────────────────────────────────────────────
# Maps fragments of a company name (lowercase) to their primary ticker.
ENTITY_TICKERS: dict[str, str] = {
    # Tech mega-cap
    "apple": "AAPL", "microsoft": "MSFT", "alphabet": "GOOGL", "google": "GOOGL",
    "amazon": "AMZN", "meta": "META", "nvidia": "NVDA", "tesla": "TSLA",
    # Semiconductors
    "amd": "AMD", "intel": "INTC", "qualcomm": "QCOM", "broadcom": "AVGO",
    "micron": "MU", "asml": "ASML", "tsmc": "TSM", "applied materials": "AMAT",
    "lam research": "LRCX", "marvell": "MRVL",
    # Pharma / biotech
    "arvinas": "ARVN", "spero": "SPRO", "merck": "MRK", "pfizer": "PFE",
    "johnson & johnson": "JNJ", "abbvie": "ABBV", "eli lilly": "LLY",
    "unicycive": "UNCY", "viridian": "VRDN", "ionis": "IONS",
    "achieve life": "ACHV",
    # Financials
    "jpmorgan": "JPM", "jp morgan": "JPM", "goldman sachs": "GS",
    "bank of america": "BAC", "citigroup": "C", "wells fargo": "WFC",
    "blackrock": "BLK",
    # Energy
    "exxon": "XOM", "chevron": "CVX", "conocophillips": "COP",
    "bp": "BP", "shell": "SHEL",
    # Consumer / retail
    "nike": "NKE", "fedex": "FDX", "costco": "COST", "walmart": "WMT",
    "victoria's secret": "VSXY",  # ticker changed VSCO→VSXY on 2026-06-02
    "kohl's": "KSS", "kohls": "KSS", "macy's": "M", "macys": "M",
    "citi trends": "CTRN", "caleres": "CAL",
    "greif": "GEF", "eplus": "PLUS", "cronos": "CRON", "accenture": "ACN",
    "adobe": "ADBE",
    # Software / IT services
    "softwareone": "SOW",
    # Aerospace / defence
    "lockheed": "LMT", "raytheon": "RTX", "northrop": "NOC",
    "boeing": "BA", "spacex": "RKLB",  # SpaceX private; RKLB as proxy
    # EV / auto
    "rivian": "RIVN", "general motors": "GM", "ford": "F",
    # Industrials / materials
    "medline": "MDLN", "solv energy": "MWH",
    # --- AI & compute ecosystem -------------------------------------------------
    # (keys chosen to avoid fragile short substrings, e.g. "arm holdings" not "arm",
    #  "cisco systems" not bare "cisco" which hits "San Francisco")
    "arm holdings": "ARM", "qualcomm": "QCOM",
    "super micro": "SMCI", "supermicro": "SMCI",
    "dell technologies": "DELL", "hewlett packard enterprise": "HPE", "hpe": "HPE",
    "arista": "ANET", "cisco systems": "CSCO", "credo": "CRDO",
    "astera labs": "ALAB", "vertiv": "VRT", "eaton": "ETN",
    "oracle": "ORCL", "coreweave": "CRWV",
    "equinix": "EQIX", "digital realty": "DLR",
    "palantir": "PLTR", "snowflake": "SNOW", "servicenow": "NOW", "salesforce": "CRM",
    "kla corporation": "KLAC",
}

# ── Sector ETF reference ───────────────────────────────────────────────────
SECTOR_ETFS: dict[str, str] = {
    "bonds":         "TLT",
    "gold":          "GLD",
    "dollar":        "UUP",
    "financials":    "XLF",
    "tech":          "XLK",
    "energy":        "XLE",
    "healthcare":    "XLV",
    "biotech":       "XBI",
    "consumer_disc": "XLY",
    "consumer_stpl": "XLP",
    "industrials":   "XLI",
    "materials":     "XLB",
    "defense":       "ITA",
    "semis":         "SOXX",
    "realestate":    "XLRE",
    "utilities":     "XLU",
    "broad_market":  "SPY",
    "launches":      "ARKX",
    "crude_oil":     "USO",
    "ai_compute":    "SMH",    # semiconductor / AI-compute proxy
    "datacenter":    "DLR",    # data-center infrastructure proxy
}


@dataclass
class Impact:
    ticker: str
    direction: int          # +1 / -1 / 0
    confidence: str         # "high" / "medium" / "low"
    reason: str             # ≤ 120 chars
    sector: str = ""

    def to_dict(self, event_uid: str) -> dict:
        return {"event_uid": event_uid, "ticker": self.ticker, "direction": self.direction,
                "confidence": self.confidence, "reason": self.reason[:120], "sector": self.sector}


# ── Keyword → impacts rules ────────────────────────────────────────────────
# Each rule: (regex_pattern, [Impact, ...])
KEYWORD_RULES: list[tuple[str, list[Impact]]] = [
    # --- Macro ---
    (r"consumer price index|CPI|inflation",
     [Impact("TLT", -1, "medium", "Hot inflation → bond prices fall, yields rise", "bonds"),
      Impact("GLD", +1, "medium", "Inflation hedge; gold tends to rally on CPI beats", "gold"),
      Impact("XLF", -1, "medium", "Higher rates pressure bank net-interest-margin expectations", "financials"),
      Impact("XLRE", -1, "medium", "Rate-sensitive; hot CPI weighs on REITs", "realestate"),
      Impact("XLP", +1, "low",    "Consumer staples benefit as inflation-pass-through sector", "consumer_stpl")]),
    (r"jobs report|employment situation|nonfarm payroll|unemployment",
     [Impact("XLY", 0,  "medium", "Jobs data drives consumer-spending outlook; direction depends on print", "consumer_disc"),
      Impact("TLT", -1, "low",    "Strong jobs → Fed less likely to cut; bonds soften", "bonds"),
      Impact("SPY", +1, "low",    "Strong employment broadly positive for equity sentiment", "broad_market")]),
    (r"GDP|gross domestic product",
     [Impact("SPY", +1, "medium", "Strong GDP revision positive for broad equities", "broad_market"),
      Impact("XLY",  +1, "medium", "Cyclicals outperform in strong-growth regime", "consumer_disc"),
      Impact("TLT", -1, "low",    "Strong growth reduces rate-cut expectations", "bonds")]),
    (r"personal income|PCE|personal consumption",
     [Impact("TLT", -1, "medium", "Hot PCE is the Fed's preferred inflation gauge; bearish bonds", "bonds"),
      Impact("GLD", +1, "low",    "PCE beat reinforces inflation theme; mild gold positive", "gold"),
      Impact("XLY", 0,  "low",    "Personal income data shapes consumer-spending outlook", "consumer_disc")]),
    (r"retail sales",
     [Impact("XLY", +1, "medium", "Strong retail sales directly lifts consumer-discretionary sector", "consumer_disc"),
      Impact("COST", +1, "low",   "Broad retail beat broadly positive for large retail names", "consumer_stpl"),
      Impact("WMT",  +1, "low",   "Retail bellwether; positive read-through on strong print", "consumer_stpl")]),
    (r"industrial production|manufacturing",
     [Impact("XLI", +1, "medium", "Industrial production beat positive for industrials sector", "industrials"),
      Impact("XLB", +1, "low",    "Strong production supports materials demand", "materials")]),
    (r"housing starts|building permits",
     [Impact("XLRE", +1, "medium", "Permits/starts beat positive for real-estate and homebuilders", "realestate"),
      Impact("XLB",  +1, "low",   "More construction drives lumber, copper and materials demand", "materials")]),
    (r"trade.{0,20}goods|current account|international trade",
     [Impact("UUP", 0,  "low",   "Trade data influences dollar; direction depends on deficit size", "dollar"),
      Impact("XLI", 0,  "low",   "Trade balance read-through for industrial exporters", "industrials")]),

    # --- Central bank ---
    (r"FOMC|rate decision|federal funds|fed chair|press conference",
     [Impact("TLT", 0,  "high",  "FOMC decision directly moves bond market; direction per decision", "bonds"),
      Impact("GLD", 0,  "high",  "Gold sensitive to real-rate outlook; direction per Fed tone", "gold"),
      Impact("XLF", 0,  "high",  "Bank stocks react to rate path signal; direction per decision", "financials"),
      Impact("XLRE", -1,"medium","Uncertainty around rate path weighs on rate-sensitive REITs", "realestate"),
      Impact("UUP", 0,  "medium","Dollar strength linked to relative rate expectations", "dollar")]),
    (r"ECB|European Central Bank",
     [Impact("TLT", 0,  "medium","ECB decision affects global rate expectations and Treasury yields", "bonds"),
      Impact("UUP", 0,  "medium","EUR/USD sensitive to ECB-Fed policy divergence", "dollar")]),
    (r"Bank of England|BoE|MPC",
     [Impact("TLT", 0,  "low",   "BoE decision can ripple through global bond markets", "bonds"),
      Impact("UUP", 0,  "low",   "GBP/USD moves on BoE surprise; indirect dollar impact", "dollar")]),
    (r"Bank of Japan|BoJ",
     [Impact("TLT", -1, "medium","BoJ yield curve control changes export Treasury selling pressure", "bonds"),
      Impact("ASML", 0, "low",   "JPY strength from BoJ shift affects Japanese tech export valuations", "semis")]),

    # --- IPO / capital markets ---
    (r"IPO|initial public offering|listing|Nasdaq debut|NYSE debut",
     [Impact("XLK", 0,  "low",   "Large tech IPOs can absorb liquidity from the broader sector", "tech"),
      Impact("ARKX", +1,"low",   "Space/aerospace IPO activity positive for launch-sector ETF", "launches")]),
    (r"capital markets day|investor day|analyst day|earnings guidance",
     [Impact("XLK", 0,  "low",   "Management guidance on strategy affects sector sentiment", "tech"),
      Impact("SPY", 0,  "low",   "Corporate guidance shifts near-term growth expectations", "broad_market")]),

    # --- AI & compute ecosystem ---
    (r"\bGPU\b|accelerator|\bRubin\b|\bBlackwell\b|MI[0-9]{3}|tape[- ]?out|AI chip|"
     r"custom silicon|\bASIC\b|inference chip",
     [Impact("NVDA", +1, "medium", "Next-gen AI accelerators expand Nvidia's compute franchise", "ai_compute"),
      Impact("SMH",  +1, "medium", "New AI silicon broadly lifts the semiconductor complex", "ai_compute"),
      Impact("AVGO", +1, "low",    "Custom-silicon demand benefits Broadcom's AI ASIC business", "ai_compute"),
      Impact("TSM",  +1, "low",    "Leading-edge AI chips are fabbed at TSMC", "ai_compute")]),
    (r"\bHBM\d?\b|high.bandwidth memory|memory bandwidth",
     [Impact("MU",   +1, "high",   "HBM demand for AI accelerators directly drives Micron pricing", "ai_compute"),
      Impact("SMH",  +1, "low",    "Tight HBM supply is a positive signal for the memory cycle", "ai_compute")]),
    (r"data ?center|hyperscale|AI cloud|supercomputer|gigawatt|liquid cooling",
     [Impact("VRT",  +1, "medium", "Data-center build-out drives demand for Vertiv power & cooling", "datacenter"),
      Impact("ANET", +1, "medium", "AI cluster networking is a tailwind for Arista switches", "datacenter"),
      Impact("DLR",  +1, "low",    "Hyperscale capacity expansion benefits data-center REITs", "datacenter"),
      Impact("NVDA", +1, "low",    "Compute build-outs ultimately consume Nvidia accelerators", "ai_compute")]),
    (r"\bClaude\b|\bGPT\b|Gemini|\bLlama\b|frontier model|large language model|\bLLM\b|foundation model",
     [Impact("NVDA", +1, "medium", "Frontier-model training & serving drives demand for AI compute", "ai_compute"),
      Impact("SMH",  +1, "low",    "Model-release cadence sustains the AI semiconductor cycle", "ai_compute"),
      Impact("MSFT", 0,  "low",    "Hyperscalers monetize frontier models via cloud AI services", "tech")]),
    # Private frontier labs → public enablers / backers basket
    (r"anthropic|openai|\bxai\b|mistral|cohere|databricks|scale ai",
     [Impact("NVDA", +1, "medium", "Private AI-lab compute spend flows to GPU supplier Nvidia", "ai_compute"),
      Impact("AMZN", +1, "low",    "Amazon is a major Anthropic backer and cloud host", "tech"),
      Impact("GOOGL",+1, "low",    "Alphabet invests in Anthropic and competes via Gemini", "tech"),
      Impact("MSFT", +1, "low",    "Microsoft's OpenAI partnership underpins its Azure AI stack", "tech")]),
    (r"SpaceX",
     [Impact("RKLB", -1,"medium","SpaceX IPO would intensify competition for Rocket Lab", "launches"),
      Impact("ARKX", +1,"medium","SpaceX listing would boost space-economy ETF weight", "launches"),
      Impact("BA",   -1,"low",   "SpaceX competitive pressure on Boeing launch business", "industrials")]),

    # --- Regulatory / FDA ---
    (r"PDUFA|FDA action|FDA approval|NDA|BLA",
     [Impact("XBI", 0,  "medium","FDA binary event drives broad biotech sentiment; direction per decision", "biotech"),
      Impact("XLV", 0,  "low",   "Healthcare sector watches major PDUFA outcomes", "healthcare")]),
    (r"antitrust|DOJ|FTC ruling|competition",
     [Impact("XLK", -1, "medium","Antitrust scrutiny on tech weighs on sector multiple", "tech"),
      Impact("GOOGL",-1,"medium","Alphabet most exposed to current antitrust proceedings", "tech"),
      Impact("META", -1,"low",   "Regulatory risk read-through for large platform companies", "tech")]),
    (r"FAA license|launch license",
     [Impact("RKLB", +1,"medium","FAA license clears path for next launch; positive for RKLB", "launches"),
      Impact("ARKX", +1,"low",   "Launch cadence positive for space-economy ETF", "launches")]),
    (r"SEC rule|securities regulation|disclosure",
     [Impact("XLF", -1,"medium","New SEC disclosure rules raise compliance costs for financials", "financials"),
      Impact("GS",  -1,"low",   "Wall Street directly affected by new securities regulations", "financials")]),

    # --- Operational / launches ---
    (r"rocket launch|satellite launch|Starlink",
     [Impact("RKLB", 0, "medium","Direct competitor intelligence; Starlink launch competes", "launches"),
      Impact("ARKX", +1,"low",   "Successful launches positive for space-economy ETF", "launches")]),
    (r"factory|production ramp|gigafactory|chip production",
     [Impact("TSLA", +1,"medium","Production milestone positive for Tesla delivery and margin outlook", "industrials"),
      Impact("NVDA", +1,"low",   "Chip-fab ramp eases supply constraint; positive for AI supply chain", "semis"),
      Impact("TSM",  +1,"medium","TSMC capacity milestone directly positive for semiconductor supply", "semis")]),

    # --- Industry / supply-demand ---
    (r"OPEC|oil output|crude|production cut",
     [Impact("USO", +1, "high",  "OPEC output cut directly supports crude oil prices", "crude_oil"),
      Impact("XOM", +1, "high",  "Higher oil price positive for Exxon earnings", "energy"),
      Impact("CVX", +1, "high",  "Higher oil price positive for Chevron earnings", "energy"),
      Impact("XLP", -1, "medium","Higher energy costs compress consumer staples margins", "consumer_stpl"),
      Impact("XLY", -1, "medium","Higher gasoline prices reduce consumer discretionary spending", "consumer_disc")]),
    (r"semiconductor|DRAM|memory pricing|chip",
     [Impact("MU",  +1, "medium","DRAM contract pricing directly affects Micron margins", "semis"),
      Impact("SOXX", +1,"medium","Positive semiconductor pricing read-through for the sector", "semis"),
      Impact("NVDA", +1,"low",   "Tight AI chip supply reinforces NVDA pricing power", "semis")]),
    (r"Paris Air Show|aerospace order|aircraft order",
     [Impact("BA",  +1, "high",  "Air Show order announcements directly drive Boeing backlog/sentiment", "industrials"),
      Impact("GE",  +1, "medium","Aircraft engine orders positive for GE Aerospace", "industrials"),
      Impact("XLI", +1, "low",   "Aerospace orders broadly positive for industrials ETF", "industrials")]),
    (r"shipping|freight|container|Baltic Dry",
     [Impact("ZIM", 0,  "medium","Container shipping rate shifts directly impact ZIM earnings", "industrials"),
      Impact("XLI", 0,  "low",   "Freight sentiment indicator for industrial supply-chain stocks", "industrials")]),

    # --- Geopolitical ---
    (r"tariff|trade war|import duty",
     [Impact("XLY", -1,"medium","Tariffs raise input costs and dampen consumer purchasing power", "consumer_disc"),
      Impact("XLI", -1,"medium","Trade friction disrupts supply chains and exports for industrials", "industrials"),
      Impact("GLD", +1,"medium","Safe-haven demand rises on trade-war escalation", "gold"),
      Impact("TSLA", -1,"low",  "China tariff retaliation risk for Tesla EV sales", "consumer_disc"),
      Impact("AAPL", -1,"medium","Apple supply chain and China revenue exposed to tariff escalation", "tech")]),
    (r"NATO|defense|military|sanctions",
     [Impact("ITA", +1,"high",  "NATO/defence events drive defence spending expectations upward", "defense"),
      Impact("LMT", +1,"high",  "Lockheed Martin directly benefits from increased defence budgets", "defense"),
      Impact("RTX", +1,"high",  "Raytheon benefits from elevated NATO spending commitments", "defense"),
      Impact("NOC", +1,"high",  "Northrop Grumman benefits from elevated defence budgets", "defense")]),
    (r"election|vote|ballot",
     [Impact("SPY", 0, "low",   "Elections introduce policy uncertainty; directional impact varies", "broad_market"),
      Impact("GLD", +1,"low",   "Political uncertainty typically supports safe-haven gold demand", "gold")]),
    (r"G7|G20|summit|diplomatic",
     [Impact("GLD", +1,"low",   "Geopolitical summits can signal macro policy shifts; gold hedges risk", "gold"),
      Impact("UUP", 0, "low",   "Communiqués on dollar/trade influence currency markets", "dollar")]),
    (r"sanctions|embargo",
     [Impact("XOM", 0, "medium","Energy sanctions reshape global oil supply/demand balance", "energy"),
      Impact("USO", 0, "medium","Sanctions on oil-producing nations move crude prices", "crude_oil"),
      Impact("ITA", +1,"low",   "Sanctions regimes often accompany defence budget increases", "defense")]),
]

# ── Category defaults ──────────────────────────────────────────────────────
CATEGORY_DEFAULTS: dict[int, list[Impact]] = {
    1: [Impact("SPY", 0, "low", "Macro data releases drive broad market sentiment; watch for surprise", "broad_market")],
    2: [Impact("TLT", 0, "low", "Central bank policy uncertainty keeps bond market on watch", "bonds"),
        Impact("GLD", 0, "low", "Rate policy shifts influence gold via real-yield channel", "gold")],
    3: [Impact("SPY", 0, "low", "Corporate earnings shape quarterly equity market narrative", "broad_market")],
    4: [Impact("XLK", 0, "low", "Strategic product/AI announcements most relevant to tech sector", "tech")],
    5: [Impact("ARKX", +1, "low","Operational milestones add evidence for space-economy ETF thesis", "launches")],
    6: [Impact("XBI", 0, "high", "FDA events are binary high-volatility catalysts for biotech", "biotech"),
        Impact("XLV", 0, "low",  "Regulatory decisions affect broader healthcare sector multiple", "healthcare")],
    7: [Impact("XLE", 0, "low",  "Industry supply-demand events move energy and materials sectors", "energy")],
    8: [Impact("GLD", +1,"low",  "Geopolitical events support safe-haven gold demand", "gold"),
        Impact("ITA", +1,"low",  "Security events typically lift defence sector sentiment", "defense")],
    9: [Impact("SMH",  +1, "low", "AI build-out broadly supports the semiconductor complex", "ai_compute"),
        Impact("NVDA", +1, "low", "Leading accelerator vendor benefits from AI-ecosystem momentum", "ai_compute")],
}


def analyze(event) -> list[Impact]:
    """Return a list of Impact objects for a single event (as dict or Event-like)."""
    if hasattr(event, "__dict__"):
        cat = event.category_id
        title = (event.title or "").lower()
        desc = (event.description or "").lower()
        entity = (event.entity or "").lower()
        uid = event.uid
    else:
        cat = event.get("category_id", 0)
        title = (event.get("title") or "").lower()
        desc = (event.get("description") or "").lower()
        entity = (event.get("entity") or "").lower()
        uid = event.get("uid", "")

    blob = f"{title} {desc} {entity}"
    impacts: list[Impact] = []
    seen_tickers: set[str] = set()

    def add(imp: Impact):
        if imp.ticker not in seen_tickers:
            seen_tickers.add(imp.ticker)
            impacts.append(imp)

    # Layer 1: entity match → direct high-confidence impact
    for fragment, ticker in ENTITY_TICKERS.items():
        if fragment in blob:
            add(Impact(ticker, 0, "high",
                       f"Direct event for {fragment.title()}; price-sensitive catalyst", ""))

    # Layer 2: keyword rules
    for pattern, rule_impacts in KEYWORD_RULES:
        if re.search(pattern, blob, flags=re.I):
            for imp in rule_impacts:
                add(imp)

    # Layer 3: category defaults (fills gaps if no keyword matched)
    if not impacts or all(i.confidence == "high" for i in impacts):
        for imp in CATEGORY_DEFAULTS.get(cat, []):
            add(imp)

    return impacts[:12]  # cap to 12 per event to keep payload lean


def analyze_all(events) -> list[dict]:
    """Analyze a list of event rows (dicts from DB) and return all impact dicts."""
    out = []
    for ev in events:
        for imp in analyze(ev):
            out.append(imp.to_dict(ev["uid"] if isinstance(ev, dict) else ev.uid))
    return out
