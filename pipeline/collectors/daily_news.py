"""Daily real-news collector — marquee tech catalysts (June–Dec 2026).

REAL data, news-sourced (source_type="scraper"). Designed to be run **daily**: it mines
Google News RSS for the latest reporting on upcoming events from the hot companies the
calendar tracks, extracts a concrete in-window date, classifies the event, and emits it.
Idempotent — dedup key is entity+date+category, so re-running daily collapses repeated
articles about the same real-world event into one row (and `INSERT OR IGNORE` in the DB
means already-stored events are never duplicated).

This is the REAL replacement for the previously-synthetic curated tech calendar: every
event here traces to a dated news report (`source_url`), not a hand-typed projection.

Confidence is inherently medium (news-extracted dates can be wrong) — verify before use.
"""
from __future__ import annotations

import re

from collectors.base import BaseCollector
from collectors.news import GNEWS, NEWS_UA, _parse_rss_date, _extract_source_name
from models import Event
from parsers import strip_tags, extract_dates_window

# ── Entity roster ────────────────────────────────────────────────────────────
# (canonical name, [lowercase aliases]). The canonical name is set as the event
# `entity`; the stock-impact engine maps it to tickers (entity match + keyword rules).
# Longest aliases first so "super micro" beats "micro", "google deepmind" beats "google".
ENTITIES: list[tuple[str, list[str]]] = [
    ("Apple",      ["apple", "iphone", "wwdc", "ipados", "macbook"]),
    ("Nvidia",     ["nvidia", "geforce", "blackwell", "rubin", "gtc"]),
    ("Tesla",      ["tesla", "robotaxi", "cybertruck", "optimus"]),
    ("SpaceX",     ["spacex", "starship", "starlink", "falcon"]),
    ("Amazon",     ["amazon web services", "amazon", "aws", "re:invent", "reinvent"]),
    ("Microsoft",  ["microsoft", "azure", "copilot", "ignite", "microsoft build"]),
    ("Alphabet",   ["alphabet", "google deepmind", "deepmind", "google", "gemini", "pixel"]),
    ("Meta",       ["meta platforms", "meta connect", "meta", "llama", "oculus"]),
    ("Micron",     ["micron"]),
    ("AMD",        ["advanced micro devices", "amd", "instinct"]),
    ("Broadcom",   ["broadcom"]),
    ("Intel",      ["intel"]),
    ("Qualcomm",   ["qualcomm", "snapdragon"]),
    ("Oracle",     ["oracle"]),
    ("TSMC",       ["taiwan semiconductor", "tsmc"]),
    ("Anthropic",  ["anthropic", "claude"]),
    ("OpenAI",     ["openai", "chatgpt", "gpt-5", "gpt-6"]),
    # High-short / activist consumer-turnaround names (VSCO/VSXY-style setups) — their
    # dated catalysts get a ⚡ setup badge via analysis/setup_signals.py.
    ("Victoria's Secret", ["victoria's secret", "victorias secret", "vsxy", "vsco"]),
    ("Kohl's",            ["kohl's", "kohls"]),
    ("Macy's",            ["macy's", "macys"]),
]

_ALIAS_INDEX = sorted(
    [(re.compile(rf"\b{re.escape(a)}\b", re.I), canon) for canon, aliases in ENTITIES for a in aliases],
    key=lambda x: -len(x[0].pattern),
)

# ── Category classifier (priority order) ─────────────────────────────────────
# Each: (category_id, compiled pattern). First match wins.
_CATEGORY_RULES: list[tuple[int, re.Pattern]] = [
    # 5 — operational milestones (space launches, robotaxi/factory/production)
    (5, re.compile(r"\b(starship|rocket|launch pad|orbital|test flight|robotaxi|"
                   r"gigafactory|factory|production ramp|first delivery|deliveries)\b", re.I)),
    # 9 — AI & compute ecosystem (chips, models, AI conferences, memory)
    (9, re.compile(r"\b(gpu|ai chip|accelerator|hbm\d?|data ?center|datacenter|"
                   r"foundation model|frontier model|\bllm\b|gtc|re:?invent|ignite|"
                   r"supercomputer|inference|semiconductor|silicon)\b", re.I)),
    # 3 — corporate financial (earnings / results)
    (3, re.compile(r"\b(earnings|quarterly results|q[1-4]\s*20\d\d|fiscal|reports? (?:results|earnings))\b", re.I)),
    # 4 — corporate strategic (product launches, keynotes, events, M&A) — default
    (4, re.compile(r"\b(launch|unveil|reveal|keynote|event|conference|announce|"
                   r"acquisition|merger|product|summit)\b", re.I)),
]

_HIGH_SIGNAL = re.compile(
    r"\b(launch|unveil|keynote|earnings|reveal|confirm[s]?|announce[sd]?|"
    r"release|debut|flight test|going live)\b", re.I)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


class DailyTechNewsCollector(BaseCollector):
    """Real, news-mined marquee tech catalysts across the full collection window."""

    source = "daily_tech_news"
    source_type = "scraper"
    category_id = 4  # nominal; each event carries its own classified category
    rate_delay = 1.0
    MAX_PER_QUERY = 8

    # Broad, evergreen queries (NOT month-locked) — the in-window date filter does the
    # narrowing, so the same query keeps surfacing fresh dates as news breaks day to day.
    QUERIES = [
        "Apple event 2026 iPhone keynote date",
        "Apple earnings date 2026",
        "Nvidia GTC 2026 keynote date",
        "Nvidia earnings date 2026",
        "Tesla Robotaxi launch 2026 city",
        "Tesla earnings date 2026",
        "SpaceX Starship next flight 2026 date",
        "AWS re:Invent 2026 dates",
        "Microsoft Ignite 2026 dates",
        "Microsoft earnings date 2026",
        "Google Pixel event 2026 date",
        "Alphabet earnings date 2026",
        "Meta Connect 2026 date",
        "Micron earnings date 2026 HBM",
        "AMD earnings date 2026 Instinct AI GPU",
        "Anthropic Claude model release 2026",
        "OpenAI GPT model release 2026",
        "AI data center launch 2026 gigawatt",
        # High-short / activist consumer-turnaround catalysts
        "Victoria's Secret VSXY earnings date 2026",
        "Kohl's earnings date 2026",
        "Macy's earnings date 2026",
    ]

    def _detect_entity(self, blob: str) -> str:
        for pat, canon in _ALIAS_INDEX:
            if pat.search(blob):
                return canon
        return ""

    def _classify(self, blob: str) -> int:
        for cat, pat in _CATEGORY_RULES:
            if pat.search(blob):
                return cat
        return 4

    def _search(self, query: str) -> list[Event]:
        from urllib.parse import quote
        url = GNEWS.format(q=quote(query))
        xml = self.http.get(url, respect_robots=False, ua=NEWS_UA)
        if not xml:
            return []
        out: list[Event] = []
        items = re.findall(r"<item>(.*?)</item>", xml, flags=re.S)
        for it in items[: self.MAX_PER_QUERY]:
            title = self._tag(it, "title")
            desc = strip_tags(self._tag(it, "description"))
            link = self._tag(it, "link")
            pub_date = _parse_rss_date(self._tag(it, "pubDate"))
            pub_source = _extract_source_name(title, link)
            blob = f"{title}. {desc}"

            dates = extract_dates_window(blob, self.month_start, self.month_end)
            if not dates:
                continue  # no precise in-window date → drop (noise control)
            entity = self._detect_entity(blob)
            if not entity:
                continue  # must be about a tracked company
            cat = self._classify(blob)
            importance = "high" if _HIGH_SIGNAL.search(blob) else "medium"

            out.append(Event(
                category_id=cat,
                title=title[:160],
                description=(desc[:300] or "Mined from a news report; verify before use."),
                event_date=dates[0],
                entity=entity,
                importance=importance,
                source=self.source,
                source_type="scraper",
                # entity+date+category dedup → repeated articles collapse to one event
                native_id=f"{_slug(entity)}:{dates[0]}:{cat}",
                source_url=link,
                pub_date=pub_date,
                pub_source=pub_source,
                raw={"query": query, "confidence": "medium", "tier": 3,
                     "pub_date": pub_date, "pub_source": pub_source},
            ))
        return out

    @staticmethod
    def _tag(item: str, tag: str) -> str:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", item, flags=re.S)
        if not m:
            return ""
        val = m.group(1)
        val = re.sub(r"<!\[CDATA\[(.*?)\]\]>", r"\1", val, flags=re.S)
        return strip_tags(val) if tag != "link" else val.strip()

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        seen: set[str] = set()
        for q in self.QUERIES:
            for ev in self._search(q):
                if ev.native_id in seen:
                    continue
                seen.add(ev.native_id)
                events.append(ev)
        self.report.notes.append(
            f"DAILY news mine: {len(events)} real, dated events ({self.month_start}…"
            f"{self.month_end}) across {len(self.QUERIES)} queries, each tied to a known "
            "company and a news source_url. News-extracted dates — verify before use."
        )
        return events
