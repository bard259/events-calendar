"""Category 9 — AI & Compute Ecosystem.

TIER 3 news mining focused on the AI build-out and the companies that drive it:

  - Silicon / accelerators ... Nvidia, AMD, Broadcom, Marvell, Arm, Qualcomm
  - Memory (HBM) ............. Micron, SK Hynix, Samsung
  - Foundry / equipment ...... TSMC, ASML, Applied Materials, Lam Research, KLA
  - Systems / contractors .... Super Micro, Dell, HPE, Foxconn
  - Networking / interconnect  Arista, Cisco, Credo, Astera Labs
  - Power / cooling .......... Vertiv, Eaton
  - Hyperscalers / cloud ..... Microsoft, Alphabet, Amazon, Oracle, Meta, CoreWeave
  - Data-center REITs ........ Equinix, Digital Realty
  - AI software .............. Palantir, Snowflake, ServiceNow, Salesforce
  - Frontier labs (private) .. Anthropic, OpenAI, xAI, Mistral, Cohere, Databricks

We mine Google News RSS for announced June-2026 milestones (chip/model launches,
data-center build-outs, supply deals, conferences) and ONLY emit when a concrete
in-window date is extractable. Crucially we also detect WHICH ecosystem company the
headline is about and set it as the event entity, so the stock-impact engine can
attach the right ticker (a private lab maps to its public enablers via keyword rules).

Dedup follows the project convention for mined events: when a company is detected the
native_id is company+date, so multiple articles about the same milestone collapse
into one row.
"""
from __future__ import annotations

import re

from collectors.news import NewsCollector
from models import Event

# (canonical name, ticker | None, [lowercase aliases], ecosystem role)
AI_ENTITIES: list[tuple[str, str | None, list[str], str]] = [
    # Silicon / accelerators
    ("Nvidia", "NVDA", ["nvidia"], "silicon"),
    ("AMD", "AMD", ["advanced micro devices", "amd"], "silicon"),
    ("Intel", "INTC", ["intel"], "silicon"),
    ("Broadcom", "AVGO", ["broadcom"], "silicon"),
    ("Marvell", "MRVL", ["marvell"], "silicon"),
    ("Arm Holdings", "ARM", ["arm holdings", "arm"], "silicon"),
    ("Qualcomm", "QCOM", ["qualcomm"], "silicon"),
    # Memory (HBM)
    ("Micron", "MU", ["micron"], "memory"),
    ("SK Hynix", None, ["sk hynix", "hynix"], "memory"),
    ("Samsung", None, ["samsung"], "memory"),
    # Foundry / equipment
    ("TSMC", "TSM", ["taiwan semiconductor", "tsmc"], "foundry"),
    ("ASML", "ASML", ["asml"], "equipment"),
    ("Applied Materials", "AMAT", ["applied materials"], "equipment"),
    ("Lam Research", "LRCX", ["lam research"], "equipment"),
    ("KLA", "KLAC", ["kla corporation", "kla corp"], "equipment"),
    # Systems / contract manufacturers
    ("Super Micro", "SMCI", ["super micro", "supermicro"], "systems"),
    ("Dell", "DELL", ["dell technologies", "dell"], "systems"),
    ("HPE", "HPE", ["hewlett packard enterprise", "hpe"], "systems"),
    ("Foxconn", None, ["foxconn", "hon hai"], "systems"),
    # Networking / interconnect
    ("Arista", "ANET", ["arista networks", "arista"], "networking"),
    ("Cisco Systems", "CSCO", ["cisco systems", "cisco"], "networking"),
    ("Credo", "CRDO", ["credo technology", "credo semiconductor"], "networking"),
    ("Astera Labs", "ALAB", ["astera labs", "astera"], "networking"),
    # Power / cooling (data-center contractors)
    ("Vertiv", "VRT", ["vertiv"], "power_cooling"),
    ("Eaton", "ETN", ["eaton"], "power_cooling"),
    # Hyperscalers / cloud
    ("Microsoft", "MSFT", ["microsoft", "azure"], "hyperscaler"),
    ("Alphabet", "GOOGL", ["alphabet", "google deepmind", "deepmind", "google"], "hyperscaler"),
    ("Amazon", "AMZN", ["amazon web services", "amazon", "aws"], "hyperscaler"),
    ("Oracle", "ORCL", ["oracle"], "hyperscaler"),
    ("Meta", "META", ["meta platforms", "meta ai", "meta"], "hyperscaler"),
    ("CoreWeave", "CRWV", ["coreweave"], "hyperscaler"),
    # Data-center REITs
    ("Equinix", "EQIX", ["equinix"], "datacenter_reit"),
    ("Digital Realty", "DLR", ["digital realty"], "datacenter_reit"),
    # AI software / platforms
    ("Palantir", "PLTR", ["palantir"], "ai_software"),
    ("Snowflake", "SNOW", ["snowflake"], "ai_software"),
    ("ServiceNow", "NOW", ["servicenow"], "ai_software"),
    ("Salesforce", "CRM", ["salesforce"], "ai_software"),
    # Frontier labs (private — no ticker; map to enablers via keyword rules)
    ("Anthropic", None, ["anthropic", "claude"], "lab"),
    ("OpenAI", None, ["openai", "chatgpt", "gpt-5", "gpt 5"], "lab"),
    ("xAI", None, ["xai", "grok"], "lab"),
    ("Mistral", None, ["mistral ai", "mistral"], "lab"),
    ("Cohere", None, ["cohere"], "lab"),
    ("Databricks", None, ["databricks"], "lab"),
]

# Pre-compiled (pattern, canonical, role), longest alias first so "super micro"
# wins over "micro" and "google deepmind" wins over "google".
_ALIAS_INDEX: list[tuple[re.Pattern, str, str]] = sorted(
    [
        (re.compile(rf"\b{re.escape(alias)}\b", re.I), canon, role)
        for canon, _t, aliases, role in AI_ENTITIES
        for alias in aliases
    ],
    key=lambda x: -len(x[0].pattern),
)

# Higher-signal milestone keywords → "high" importance, else "medium".
_HIGH_SIGNAL = re.compile(
    r"launch|unveil|announce[sd]?|release[sd]?|general availability|\bGA\b|"
    r"ships?|debut|keynote|tape[- ]?out|go(es)? live|opening|breaks? ground",
    re.I,
)

# Relevance gate: an entity-less headline must contain at least one of these AI/compute
# terms to belong in this lane — keeps Google News noise (horoscopes, sports) out.
_AI_TERMS = re.compile(
    r"\b(AI|GPU|HBM\d?|chips?|silicon|accelerator|data ?center|datacenter|"
    r"model|LLM|inference|training|semiconductor|cloud|supercomputer|foundry|"
    r"wafer|compute|neural|GenAI|generative)\b",
    re.I,
)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


class AiIndustryCollector(NewsCollector):
    """AI & compute-ecosystem milestone miner (Tier 3, news)."""

    source = "google_news_ai"
    category_id = 9
    MAX_PER_QUERY = 6
    QUERIES = [
        # Silicon / accelerators
        '"June 2026" Nvidia (GPU OR Rubin OR Blackwell OR chip OR launch)',
        '"June 2026" AMD (Instinct OR MI400 OR MI450 OR GPU OR accelerator)',
        '"June 2026" (Broadcom OR Marvell) (AI chip OR custom silicon OR ASIC)',
        # Memory (HBM)
        '"June 2026" Micron (HBM OR HBM4 OR memory OR production OR earnings)',
        '"June 2026" (SK Hynix OR Samsung) (HBM OR memory OR AI)',
        # Foundry / equipment
        '"June 2026" TSMC (capacity OR fab OR HBM OR advanced packaging OR CoWoS)',
        # Frontier labs / models
        '"June 2026" (Anthropic OR Claude) (model OR release OR launch OR funding)',
        '"June 2026" (OpenAI OR GPT) (model OR release OR launch)',
        '"June 2026" (Gemini OR DeepMind OR Llama OR Mistral OR xAI OR Grok) (model OR release)',
        # Hyperscaler / data-center build-out
        '"June 2026" (data center OR datacenter) (AI OR capacity OR opening OR gigawatt)',
        '"June 2026" (CoreWeave OR Oracle) (AI cloud OR capacity OR supercomputer)',
        '"June 2026" (Supermicro OR Dell OR Vertiv OR Arista) (AI OR server OR deployment)',
        # Conferences / partnerships / capex
        '"June 2026" (Computex OR "Snowflake Summit" OR "Databricks" OR "Microsoft Build")',
        '"June 2026" AI (partnership OR supply deal OR investment OR capex OR expansion)',
    ]

    def _detect_entity(self, blob: str) -> tuple[str, str]:
        """Return (canonical_name, role) of the first matched ecosystem company, else ('','')."""
        for pat, canon, role in _ALIAS_INDEX:
            if pat.search(blob):
                return canon, role
        return "", ""

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        seen: set[str] = set()
        n_with_entity = 0
        n_dropped = 0
        for q in self.QUERIES:
            for ev in self._search(q):
                blob = f"{ev.title} {ev.description}"
                entity, role = self._detect_entity(blob)
                # Relevance gate: keep only ecosystem-company events or clearly AI/compute
                # headlines; drop off-topic Google News noise (horoscopes, sports, etc.).
                if not entity and not _AI_TERMS.search(blob):
                    n_dropped += 1
                    continue
                if entity:
                    ev.entity = entity
                    n_with_entity += 1
                    # company+date dedup (project convention for mined events)
                    ev.native_id = f"{_slug(entity)}:{ev.event_date}"
                    ev.raw["ecosystem_role"] = role
                ev.importance = "high" if _HIGH_SIGNAL.search(blob) else "medium"
                ev.raw["tier"] = 3
                if ev.native_id in seen:
                    continue
                seen.add(ev.native_id)
                events.append(ev)
        self.report.notes.append(
            f"TIER 3 (AI ecosystem): mined {len(events)} June-2026 milestones across "
            f"{len(self.QUERIES)} queries; {n_with_entity} matched a known ecosystem "
            f"company (entity set so stock impacts attach); {n_dropped} off-topic "
            "headlines filtered. News-mined — verify before use."
        )
        return events
