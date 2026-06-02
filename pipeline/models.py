"""Data structures shared across the pipeline."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


@dataclass
class Event:
    """A single calendar event in one of the 8 tracked categories."""

    category_id: int
    title: str
    event_date: str                 # ISO date "YYYY-MM-DD"
    source: str                     # short source slug, e.g. "launch_library_2"
    source_type: str                # "api" | "scraper" | "synthetic"
    native_id: str                  # id within the source (used for dedup)
    description: str = ""
    event_datetime: str | None = None   # ISO datetime if a precise time is known
    entity: str = ""                # company / agency / country
    importance: str = "medium"      # "low" | "medium" | "high"
    source_url: str = ""
    pub_date: str | None = None     # when the SOURCE published/filed this info (e.g. article pubDate, SEC file_date)
    pub_source: str | None = None   # name of the outlet / agency that published it (e.g. "Reuters", "SEC EDGAR", "BLS")
    raw: dict = field(default_factory=dict)
    collected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def uid(self) -> str:
        base = f"{self.source}:{self.native_id}"
        # keep it stable + short
        return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16] + ":" + self.source

    def to_row(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        d["uid"] = self.uid
        d["raw_json"] = json.dumps(self.raw, ensure_ascii=False, default=str)
        return d


@dataclass
class CollectorReport:
    """Per-collector outcome for a single run — surfaced in the final report."""

    collector: str
    category_id: int
    source_type: str
    status: str = "ok"              # "ok" | "partial" | "failed"
    events_collected: int = 0
    http_requests: int = 0
    rate_limited: bool = False
    tos_issues: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    duration_s: float = 0.0
