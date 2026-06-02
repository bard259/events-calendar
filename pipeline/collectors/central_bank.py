"""Category 2 — Central Bank & Policy.

TIER 1 (Fed): parse federalreserve.gov FOMC calendar — exact June meeting days.
TIER 3 (intl CBs): ECB/BoE/BoJ don't publish machine-readable free calendars, so we
mine their meeting dates from Google News. Treasury refunding settlement dates are
derived from the known quarterly cycle (1st business day of month following auction).
"""
from __future__ import annotations

import re

from collectors.base import BaseCollector
from collectors.news import NewsCollector, _parse_rss_date, _extract_source_name
from models import Event
from parsers import extract_dates

FOMC_URL = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FOMC_FALLBACK = ["2026-06-16", "2026-06-17"]

# Known non-scrape-able policy dates (Treasury cycle is deterministic)
FIXED = [
    ("2026-06-02", "U.S. Treasury quarterly refunding settlement", "U.S. Treasury",
     "medium", "Settlement of quarterly refunding securities issued in May 2026."),
]


class CentralBankCollector(BaseCollector):
    source = "federal_reserve_scrape"
    source_type = "scraper"
    category_id = 2
    rate_delay = 1.0

    def _parse_fomc_june(self, html: str) -> list[str]:
        start = html.find("2026 FOMC Meetings")
        end = html.find("2025 FOMC Meetings")
        segment = html[start:end] if (start != -1 and end != -1) else html
        days: list[int] = []
        for m in re.finditer(
            r"fomc-meeting__month[^>]*>\s*<strong>\s*June\s*</strong>.*?"
            r"fomc-meeting__date[^>]*>\s*([0-9–\-]+)",
            segment, flags=re.S | re.I,
        ):
            for part in re.split(r"[–\-]", m.group(1)):
                part = part.strip()
                if part.isdigit() and 1 <= int(part) <= 30:
                    days.append(int(part))
        return [f"2026-06-{d:02d}" for d in sorted(set(days))]

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        html = self.http.get(FOMC_URL)
        fomc_days: list[str] = []
        if html:
            fomc_days = self._parse_fomc_june(html)
            self.report.notes.append(
                f"Parsed FOMC June 2026 meeting day(s): {', '.join(fomc_days) or 'none found'}")
        if not fomc_days:
            fomc_days = FOMC_FALLBACK
            self.report.notes.append("Using FOMC fallback dates.")

        for i, day in enumerate(fomc_days):
            is_decision = (i == len(fomc_days) - 1)
            events.append(Event(
                category_id=2,
                title=("FOMC rate decision + SEP + press conference" if is_decision
                       else "FOMC meeting begins (Day 1)"),
                description=("Federal funds target decision, Summary of Economic "
                             "Projections, and Chair press conference." if is_decision
                             else "Two-day FOMC meeting begins."),
                event_date=day, entity="Federal Reserve", importance="high",
                source=self.source, source_type="scraper",
                native_id=f"fomc-2026-06-{day}", source_url=FOMC_URL,
                pub_source="Federal Reserve", pub_date=None))

        for date, title, entity, imp, desc in FIXED:
            events.append(Event(
                category_id=2, title=title, description=desc, event_date=date,
                entity=entity, importance=imp, source="treasury_cycle",
                source_type="scraper", native_id=title,
                pub_source="U.S. Treasury", pub_date=None))
        return events


class IntlCentralBankCollector(NewsCollector):
    """ECB, BoE, BoJ, RBA — mined from news since no free parseable calendar."""
    source = "google_news_cb_intl"
    category_id = 2
    MAX_PER_QUERY = 4
    QUERIES = [
        '"ECB" OR "European Central Bank" rate decision "June 2026"',
        '"Bank of England" OR "BoE" rate decision "June 2026"',
        '"Bank of Japan" OR "BoJ" policy decision "June 2026"',
    ]

    def fetch(self) -> list[Event]:
        events = super().fetch()
        for ev in events:
            ev.importance = "high"
        return events
