"""TIER 3 — news / press-release mining (Google News RSS, free, no key).

This is the NOISY tier the user explicitly opted into. News headlines mention future
events ("Apple confirms event for June 8"), but extracting a precise, correct date from
free text is error-prone. We mitigate by:
  - only emitting an event when an in-window June-2026 date is extractable from the
    title/description,
  - tagging everything importance="low" and source_type="scraper",
  - recording a clear noise/confidence warning in the run report.
Curated calendars remain the high-confidence backbone for cats 4 and 8.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse
from email.utils import parsedate_to_datetime

from collectors.base import BaseCollector
from models import Event
from parsers import strip_tags, extract_dates


def _parse_rss_date(pub_raw: str) -> str | None:
    """Parse RSS pubDate ('Sat, 16 May 2026 07:00:00 GMT') → ISO date '2026-05-16'."""
    if not pub_raw:
        return None
    try:
        return parsedate_to_datetime(pub_raw).strftime("%Y-%m-%d")
    except Exception:
        return None


def _extract_source_name(title: str, link: str) -> str:
    """Best-effort outlet name: trailing '- Outlet Name' in title, or the domain."""
    # Google News titles often end with "... - Outlet Name"
    m = re.search(r"\s+-\s+([^-]{3,50})\s*$", title)
    if m:
        return m.group(1).strip()
    try:
        netloc = urlparse(link).netloc
        return re.sub(r"^www\.", "", netloc)
    except Exception:
        return ""

GNEWS = ("https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en")
NEWS_UA = "Mozilla/5.0 (compatible; EventsPipeline/1.0)"


class NewsCollector(BaseCollector):
    """Base for RSS-mined collectors. Subclasses set category_id, source slug, QUERIES."""

    source_type = "scraper"
    rate_delay = 1.0
    QUERIES: list[str] = []
    MAX_PER_QUERY = 6

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
            pub_raw = self._tag(it, "pubDate")           # e.g. "Sat, 16 May 2026 07:00:00 GMT"
            pub_date = _parse_rss_date(pub_raw)           # -> "2026-05-16"
            pub_source = _extract_source_name(title, link)
            blob = f"{title}. {desc}"
            dates = extract_dates(blob, 2026, 6)
            if not dates:
                continue  # no precise in-window date -> drop (noise control)
            out.append(Event(
                category_id=self.category_id,
                title=title[:160],
                description=(desc[:300] or "Mined from a news headline; verify before use."),
                event_date=dates[0], entity="", importance="low",
                source=self.source, source_type="scraper",
                native_id=f"{self.source}-{link[-60:] or title[:60]}",
                source_url=link,
                pub_date=pub_date,
                pub_source=pub_source,
                raw={"query": query, "confidence": "low", "tier": 3,
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
            f"TIER 3 (noisy): Google News RSS mined {len(events)} low-confidence events "
            f"with an extractable June-2026 date across {len(self.QUERIES)} queries. "
            "These are tagged importance=low; treat as leads, not confirmed events.")
        return events


class StrategicNewsCollector(NewsCollector):
    source = "google_news_strategic"
    category_id = 4
    QUERIES = [
        '"June 2026" product launch',
        '"June 2026" Apple event',
        '"June 2026" AI announcement',
        '"June 2026" acquisition OR merger',
    ]


class GeopoliticalNewsCollector(NewsCollector):
    source = "google_news_geopolitical"
    category_id = 8
    QUERIES = [
        '"June 2026" election',
        '"June 2026" summit',
        '"June 2026" tariff OR sanctions',
    ]
