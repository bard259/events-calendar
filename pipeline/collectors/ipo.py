"""Category 3 (capital markets) — IPOs / going-public events.

These were missing before: an IPO is a corporate financial / capital-markets catalyst, so
it belongs in category 3. Two collectors:

  * IpoEdgarCollector  — REAL, dated IPOs scraped from SEC EDGAR full-text search:
      - 424B4 (final prospectus) filed in-window  -> IPO priced / listing day
      - S-1 / S-1/A        filed in-window        -> IPO registration filed
    Both filtered by the phrase "initial public offering" to exclude debt/ETF shelf
    prospectuses (424B4 is also used for non-IPO offerings).

  * IpoNewsCollector   — marquee RUMORED IPOs that aren't in EDGAR yet because the issuer
    is still private (e.g. SpaceX, Stripe). Mined from Google News RSS; only emitted when a
    concrete June-2026 date is reported (e.g. "SpaceX IPO on June 12"). Tagged low/medium
    confidence — treat as a lead.
"""
from __future__ import annotations

from collectors.base import BaseCollector
from collectors.news import NewsCollector
from models import Event
import edgar_fts


class IpoEdgarCollector(BaseCollector):
    source = "sec_edgar_ipo"
    source_type = "api"
    category_id = 3
    rate_delay = 0.4

    # (form, label, importance) — 424B4 ≈ pricing day; S-1 ≈ registration.
    FORM_QUERIES = [
        ("424B4", "IPO priced / began trading", "high"),
        ("S-1", "IPO registration filed (S-1)", "medium"),
        ("S-1/A", "IPO registration amended (S-1/A)", "low"),
    ]

    def fetch(self) -> list[Event]:
        out: list[Event] = []
        seen: set[str] = set()
        total = 0
        for form, label, imp in self.FORM_QUERIES:
            hits = edgar_fts.search(
                self.http, "initial public offering", forms=form,
                startdt=self.month_start, enddt=self.month_end, limit=20)
            for h in hits:
                date = h["file_date"]
                if not self.in_window(date):
                    continue
                co = h["company"] or h["ticker"] or "Issuer"
                key = f"{(h['ticker'] or co).upper()}-{form}-{date}"
                if key in seen:
                    continue
                seen.add(key)
                tk = f" ({h['ticker']})" if h["ticker"] else ""
                out.append(Event(
                    category_id=3,
                    title=f"{co}{tk}: {label}",
                    description=f"{form} filed with the SEC on {date} "
                                f"(filtered on \"initial public offering\").",
                    event_date=date, entity=co, importance=imp,
                    source=self.source, source_type="api",
                    native_id=key, source_url=h["url"],
                    raw={"form": form, "ticker": h["ticker"], "cik": h["cik"]}))
                total += 1
        # Informational: how many issuers are in the IPO pipeline right now (registered
        # in the ~45 days before the window). These have no June date yet, so they are
        # NOT emitted as calendar events — but the count shows the collector is live and
        # explains why in-window pricings may be 0 early in the month.
        import datetime
        start = (datetime.date.fromisoformat(self.month_start)
                 - datetime.timedelta(days=45)).isoformat()
        pipe = edgar_fts.search(self.http, "initial public offering", forms="S-1",
                                startdt=start, enddt=self.month_start, limit=1)
        self.report.notes.append(
            f"SEC EDGAR IPO scan: {total} dated in-window IPO events (424B4 pricings + "
            "S-1 registrations). In-window pricings fill in as the month progresses. "
            "IPO registration pipeline is active (recent S-1 filings present: "
            f"{'yes' if pipe else 'none found'}).")
        return out


class IpoNewsCollector(NewsCollector):
    """Rumored/anticipated marquee IPOs not yet in EDGAR (still-private issuers)."""

    source = "google_news_ipo"
    category_id = 3
    MAX_PER_QUERY = 5
    # query -> (entity, importance) used to label + semantically dedup by entity+date.
    QUERY_META = {
        '"SpaceX" IPO June 2026': ("SpaceX", "high"),
        '"Stripe" IPO 2026': ("Stripe", "high"),
        '"Databricks" IPO 2026': ("Databricks", "medium"),
        '"Anthropic" OR "OpenAI" IPO 2026': ("AI labs", "medium"),
        'IPO "June 2026" Nasdaq OR NYSE': ("(various)", "low"),
    }
    QUERIES = list(QUERY_META.keys())

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        seen: set[str] = set()
        for q in self.QUERIES:
            entity, imp = self.QUERY_META[q]
            for ev in self._search(q):
                # Collapse all articles about the same anticipated IPO on the same day.
                key = f"{entity}-{ev.event_date}"
                if key in seen:
                    continue
                seen.add(key)
                ev.entity = entity
                ev.importance = imp
                ev.title = f"{entity} IPO (reported): {ev.title}"[:160]
                ev.native_id = f"ipo-news-{key}"
                ev.raw["anticipated"] = True
                events.append(ev)
        self.report.notes.append(
            f"TIER 3 (rumored IPOs): mined {len(events)} anticipated IPO events with a "
            "reported June-2026 date (e.g. SpaceX). Confidence varies; verify before use.")
        return events
