"""Category 7 — Industry & Supply-Demand Events.

TIER 1 (EIA): EIA publishes weekly petroleum status reports on Wednesdays; monthly
Short-Term Energy Outlook on the 2nd Tuesday. Scraped from eia.gov.
TIER 3 (news): OPEC (403d), sector conferences, DRAM pricing, shipping events — mined
from Google News where a June 2026 date is explicitly stated.
"""
from __future__ import annotations

import re

from collectors.base import BaseCollector
from collectors.news import NewsCollector
from models import Event
from parsers import strip_tags, extract_dates

EIA_RELEASES = "https://www.eia.gov/petroleum/supply/weekly/"


class EiaCollector(BaseCollector):
    """EIA petroleum/energy release schedule — scraped."""
    source = "eia_calendar_scrape"
    source_type = "scraper"
    category_id = 7
    rate_delay = 1.0

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        html = self.http.get(EIA_RELEASES)
        if html:
            # EIA petroleum page embeds next release dates in a "release" section
            for m in re.finditer(r"(June\s+\d{1,2},\s+2026)[^\n]*", html, re.I):
                full = m.group(0).strip()
                iso = extract_dates(full, 2026, 6)
                if not iso:
                    continue
                label = strip_tags(full)[:100] or "Weekly Petroleum Status Report"
                events.append(Event(
                    category_id=7,
                    title=f"EIA Weekly Petroleum Status Report",
                    description=f"EIA weekly crude and product inventory release ({label}).",
                    event_date=iso[0], entity="EIA", importance="medium",
                    source=self.source, source_type="scraper",
                    native_id=f"eia-{iso[0]}", source_url=EIA_RELEASES,
                    pub_source="EIA.gov", pub_date=None))
            # Dedupe by date
            seen = set()
            events = [e for e in events if not (e.event_date in seen or seen.add(e.event_date))]
            self.report.notes.append(f"EIA petroleum page: {len(events)} June 2026 release dates parsed.")
        else:
            self.report.notes.append("EIA page unavailable.")
        return events


class IndustryNewsCollector(NewsCollector):
    """OPEC, semiconductor conferences, DRAM pricing, shipping — news-mined."""
    source = "google_news_industry"
    category_id = 7
    MAX_PER_QUERY = 5
    QUERIES = [
        '"OPEC" meeting "June 2026"',
        '"semiconductor" OR "DRAM" conference "June 2026"',
        '"Paris Air Show" 2026',
        '"shipping" OR "freight" disruption "June 2026"',
        '"oil" OR "natural gas" "June 2026" supply',
    ]

    def fetch(self) -> list[Event]:
        events = super().fetch()
        for ev in events:
            ev.importance = "medium"
        return events
