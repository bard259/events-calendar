"""BaseCollector: common lifecycle + report/ http wiring for every source."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

from http_client import HttpClient
from models import Event, CollectorReport


class BaseCollector(ABC):
    #: short slug, e.g. "launch_library_2"
    source: str = "unknown"
    #: "api" | "scraper" | "synthetic"
    source_type: str = "synthetic"
    #: which of the 8 categories this feeds
    category_id: int = 0
    #: politeness delay between requests (seconds)
    rate_delay: float = 0.5

    def __init__(self, month_start: str, month_end: str):
        self.month_start = month_start
        self.month_end = month_end
        self.report = CollectorReport(
            collector=self.source,
            category_id=self.category_id,
            source_type=self.source_type,
        )
        self.http = HttpClient(self.report, rate_delay=self.rate_delay)

    def in_window(self, iso_date: str) -> bool:
        return self.month_start <= iso_date <= self.month_end

    @abstractmethod
    def fetch(self) -> list[Event]:
        """Return events for the target window. Implementations must not raise."""
        ...

    def run(self) -> tuple[list[Event], CollectorReport]:
        t0 = time.monotonic()
        events: list[Event] = []
        try:
            events = [e for e in self.fetch() if self.in_window(e.event_date)]
        except Exception as e:  # collectors should handle their own errors; this is a net
            self.report.errors.append(f"unhandled: {type(e).__name__}: {e}")
            self.report.status = "failed"
        self.report.events_collected = len(events)
        if self.report.status == "ok" and self.report.errors:
            self.report.status = "partial"
        self.report.duration_s = round(time.monotonic() - t0, 3)
        return events, self.report
