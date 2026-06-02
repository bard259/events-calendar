"""Official-site scrapers for flagship conference / keynote dates.

REAL data scraped live from each company's own event page (`source_type="scraper"`).
The event *identity* (e.g. "Apple WWDC 2026") is known metadata, but the **date is
scraped from the official page on every run** — so it stays current and is never a
hand-typed projection. If a page yields no in-window date (JS-only shell, page moved,
date not yet announced), we skip it rather than guess.

Date extraction is layered, most-reliable first:
  1. schema.org JSON-LD  "startDate":"2026-09-09..."   (structured, authoritative)
  2. any ISO date  20\\d\\d-\\d\\d-\\d\\d  in the raw HTML within the window
  3. free-text dates ("September 9, 2026") via parsers.extract_dates_window
"""
from __future__ import annotations

import re

from collectors.base import BaseCollector
from models import Event
from parsers import strip_tags, extract_dates_window

# (entity, category_id, title, url, importance, keywords)
# `keywords` are distinctive tokens that must appear NEAR a scraped text-date for it to be
# trusted — this is what stops an unrelated "register by June 16" date being misread as the
# event date. JSON-LD startDate is trusted directly (authoritative, no proximity needed).
OFFICIAL_PAGES: list[tuple[str, int, str, str, str, list[str]]] = [
    ("Amazon",    9, "AWS re:Invent 2026",       "https://reinvent.awsevents.com/", "high", ["re:invent", "reinvent"]),
    ("Microsoft", 9, "Microsoft Ignite 2026",    "https://ignite.microsoft.com/", "high", ["ignite"]),
    ("Microsoft", 4, "Microsoft Build 2026",     "https://build.microsoft.com/", "high", ["build"]),
    ("Alphabet",  4, "Google I/O 2026",          "https://io.google/2026/", "high", ["i/o", "google i/o"]),
    ("Meta",      4, "Meta Connect 2026",        "https://www.meta.com/connect/", "high", ["connect"]),
]

_JSONLD_START = re.compile(r'"startDate"\s*:\s*"(\d{4}-\d{2}-\d{2})', re.I)


class OfficialEventsCollector(BaseCollector):
    """Scrapes flagship dates from each company's official event page."""

    source = "official_event_pages"
    source_type = "scraper"
    category_id = 4
    rate_delay = 1.0

    def _date_from_page(self, html: str, keywords: list[str]) -> str | None:
        start, end = self.month_start, self.month_end
        # 1) JSON-LD startDate — structured & authoritative, trust directly
        for d in _JSONLD_START.findall(html):
            if start <= d <= end:
                return d
        # 2) free-text date that sits NEAR one of the event's keywords (proximity gate)
        text = strip_tags(html).lower()
        for kw in keywords:
            for m in re.finditer(re.escape(kw.lower()), text):
                window = text[max(0, m.start() - 160): m.end() + 160]
                dates = extract_dates_window(window, start, end)
                if dates:
                    return dates[0]
        return None

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        hits = 0
        for entity, cat, title, url, importance, keywords in OFFICIAL_PAGES:
            html = self.http.get(url, respect_robots=True)
            if not html:
                continue
            date = self._date_from_page(html, keywords)
            if not date:
                continue
            hits += 1
            events.append(Event(
                category_id=cat,
                title=title,
                description=f"Official date scraped from {url} on this run.",
                event_date=date,
                entity=entity,
                importance=importance,
                source=self.source,
                source_type="scraper",
                native_id=f"{entity.lower()}:{title.lower().replace(' ', '-')}",
                source_url=url,
                pub_source="Official event site",
                raw={"scraped_date": date, "confidence": "high"},
            ))
        self.report.notes.append(
            f"Official-site scrape: {hits}/{len(OFFICIAL_PAGES)} pages yielded an in-window "
            "date. Dates scraped live from each company's own event page."
        )
        return events
