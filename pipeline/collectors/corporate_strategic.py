"""Category 4 — Corporate Strategic Catalysts.

Scraped from Google News: product launches, AI roadmaps, M&A, restructuring.
Tier 3 (news-mined) — only emits when a concrete June 2026 date is in the headline.
"""
from __future__ import annotations

from collectors.news import NewsCollector
from models import Event


class CorporateStrategicCollector(NewsCollector):
    source = "google_news_strategic"
    category_id = 4
    MAX_PER_QUERY = 6
    # NOTE: AI-ecosystem product/model events have their own dedicated lane
    # (category 9, collectors/ai_industry.py), so the AI query is intentionally
    # omitted here to avoid duplicating those events across two categories.
    QUERIES = [
        '"June 2026" product launch announcement',
        '"WWDC" OR "Apple" event "June 2026"',
        '"June 2026" acquisition OR merger announced',
        '"June 2026" investor day OR shareholder meeting',
    ]

    def fetch(self) -> list[Event]:
        events = super().fetch()
        for ev in events:
            ev.importance = "medium"
        return events
