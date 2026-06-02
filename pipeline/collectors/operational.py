"""Category 5 — Operational Milestones.

Live source: Launch Library 2 (thespacedevs) — free, no API key.
Note: the free tier is rate-limited (~15 req/hr anonymous); HttpClient records any
429s and Retry-After hints.
"""
from __future__ import annotations

from collectors.base import BaseCollector
from models import Event

LL2_BASE = "https://ll.thespacedevs.com/2.2.0/launch/"


class OperationalCollector(BaseCollector):
    source = "launch_library_2"
    source_type = "api"
    category_id = 5
    rate_delay = 1.0  # be gentle with the free tier
    LIMIT = 50        # max launches to request (raise for a multi-month window)

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        url = (
            f"{LL2_BASE}?net__gte={self.month_start}T00:00:00Z"
            f"&net__lte={self.month_end}T23:59:59Z&limit={self.LIMIT}&mode=detailed"
        )
        # API source: ToS honored via declared User-Agent + rate limiting, not robots.txt
        data = self.http.get_json(url, respect_robots=False)
        if data and "results" in data:
            for r in data["results"]:
                net = r.get("net") or ""
                date = net[:10]
                lsp = (r.get("launch_service_provider") or {}).get("name", "")
                pad = (r.get("pad") or {})
                loc = (pad.get("location") or {}).get("name", "")
                mission = (r.get("mission") or {})
                events.append(Event(
                    category_id=5,
                    title=r.get("name", "Rocket launch"),
                    description=(mission.get("description") or
                                 f"Launch from {loc}.")[:500],
                    event_date=date,
                    event_datetime=net or None,
                    entity=lsp,
                    importance="high" if any(
                        k in (r.get("name", "").lower())
                        for k in ("crew", "starship", "artemis", "moon", "lunar")
                    ) else "medium",
                    source=self.source,
                    source_type="api",
                    native_id=str(r.get("id")),
                    source_url=r.get("url", ""),
                    raw={"status": (r.get("status") or {}).get("name"),
                         "location": loc, "provider": lsp},
                ))
            self.report.notes.append(
                f"Launch Library 2 reported {data.get('count')} launches in window")
        else:
            self.report.notes.append("LL2 returned no data")

        return events
