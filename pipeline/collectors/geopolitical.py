"""Category 8 — Geopolitical & Security Events.

All real events, news-mined. No curated synthetic data.
TIER 3: Google News RSS — elections, summits, tariffs, sanctions, diplomatic meetings.
Only emits when a precise June 2026 date is extractable from the headline/description.
"""
from __future__ import annotations

from collectors.news import NewsCollector
from models import Event


class GeopoliticalCollector(NewsCollector):
    source = "google_news_geopolitical"
    category_id = 8
    MAX_PER_QUERY = 6
    QUERIES = [
        'election "June 2026"',
        '"G7" summit "June 2026"',
        '"NATO" summit "June 2026"',
        'tariff OR sanctions deadline "June 2026"',
        'diplomatic summit OR meeting "June 2026"',
        '"trade" deal OR agreement "June 2026"',
    ]

    def fetch(self) -> list[Event]:
        events = super().fetch()
        for ev in events:
            if ev.importance == "low":
                ev.importance = "medium"
        return events
