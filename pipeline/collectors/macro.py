"""Category 1 — Macro & Economic Data.

TIER 1: Both BLS and BEA publish their release schedules publicly. We scrape and parse both.
Non-BLS/BEA releases (ISM, Conference Board, ADP) come from a news-mined calendar as no
single free API covers them all.
"""
from __future__ import annotations

import re

from collectors.base import BaseCollector
from collectors.news import NewsCollector
from models import Event
from parsers import strip_tags, parse_time_to_iso, extract_dates

BLS_SCHEDULE = "https://www.bls.gov/schedule/2026/home.htm"
BEA_SCHEDULE = "https://www.bea.gov/news/schedule"

HIGH_SIGNAL = ("Employment Situation", "Consumer Price Index", "Producer Price",
               "Personal Income and Outlays", "GDP")


class MacroCollector(BaseCollector):
    source = "bls_schedule_scrape"
    source_type = "scraper"
    category_id = 1
    rate_delay = 1.0

    def _parse_bls(self, html: str) -> list[Event]:
        events: list[Event] = []
        start = html.find("June 2026")
        segment = html[start:] if start != -1 else html
        nxt = re.search(r"(July|August)\s+2026", segment)
        if nxt:
            segment = segment[: nxt.start()]
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", segment, flags=re.S | re.I):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)
            if len(cells) < 3:
                continue
            date_txt = strip_tags(cells[0])
            time_txt = strip_tags(cells[1])
            release = strip_tags(cells[2])
            iso = extract_dates(date_txt, 2026, 6)
            if not iso:
                continue
            date = iso[0]
            imp = "high" if any(h in release for h in HIGH_SIGNAL) else "medium"
            events.append(Event(
                category_id=1, title=release[:160],
                description=f"Scheduled BLS data release at {time_txt} ET.",
                event_date=date, event_datetime=parse_time_to_iso(date, time_txt),
                entity="BLS", importance=imp, source=self.source, source_type="scraper",
                native_id=f"bls-{date}-{release[:40]}", source_url=BLS_SCHEDULE,
                pub_source="BLS.gov", pub_date=None))
        return events

    def _parse_bea(self, html: str) -> list[Event]:
        events: list[Event] = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I):
            cells = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)
            if len(cells) < 3:
                continue
            date_txt = strip_tags(cells[0])
            time_txt = strip_tags(cells[1]) if len(cells) > 1 else ""
            release = strip_tags(cells[-1])
            # BEA dates look like "June 25" or "June 25 8:30 AM"
            iso = extract_dates(date_txt + " " + release, 2026, 6)
            if not iso:
                continue
            date = iso[0]
            imp = "high" if any(h in release for h in HIGH_SIGNAL) else "medium"
            events.append(Event(
                category_id=1, title=release[:160],
                description=f"Scheduled BEA economic data release at 8:30 AM ET.",
                event_date=date, event_datetime=parse_time_to_iso(date, "8:30 AM"),
                entity="BEA", importance=imp, source="bea_schedule_scrape",
                source_type="scraper",
                native_id=f"bea-{date}-{release[:40]}", source_url=BEA_SCHEDULE,
                pub_source="BEA.gov", pub_date=None))
        return events

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        html = self.http.get(BLS_SCHEDULE)
        if html:
            bls_events = self._parse_bls(html)
            events.extend(bls_events)
            self.report.notes.append(f"Parsed {len(bls_events)} BLS releases for June 2026.")
        else:
            self.report.notes.append("BLS schedule unavailable.")

        html2 = self.http.get(BEA_SCHEDULE)
        if html2:
            bea_events = self._parse_bea(html2)
            events.extend(bea_events)
            self.report.notes.append(f"Parsed {len(bea_events)} BEA releases for June 2026.")
        else:
            self.report.notes.append("BEA schedule unavailable.")
        return events


class MacroNewsCollector(NewsCollector):
    """Tier 3: ISM, ADP, Conference Board releases — no free parseable calendar."""
    source = "google_news_macro"
    category_id = 1
    MAX_PER_QUERY = 4
    QUERIES = [
        '"ISM" "June 2026" manufacturing OR services PMI',
        '"ADP" employment "June 2026"',
        '"Conference Board" "June 2026" consumer confidence',
    ]

    def fetch(self) -> list[Event]:
        events = super().fetch()
        for ev in events:
            ev.importance = "medium"
        return events
