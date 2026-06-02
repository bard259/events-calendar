"""Estimate the storage footprint BEFORE collecting.

Produces a per-category and total estimate based on expected event counts and a
representative average serialized-event size, plus SQLite overhead assumptions.
"""
from __future__ import annotations

import json

from config import CATEGORIES, EXPECTED_COUNTS
from models import Event

# A representative "average" event used to derive bytes-per-row.
SAMPLE = Event(
    category_id=3,
    title="Broadcom Q2 FY26 earnings call and guidance update",
    description=("Quarterly earnings release with management guidance commentary; "
                 "includes segment revenue detail and capital-return updates."),
    event_date="2026-06-05",
    event_datetime="2026-06-05T21:00:00Z",
    entity="Broadcom Inc.",
    importance="high",
    source="sec_edgar",
    source_type="api",
    native_id="0001234567-26-000123",
    source_url="https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=1730168",
    raw={"form": "8-K", "cik": 1730168, "items": "2.02,9.01"},
)

# SQLite per-row overhead (indexes on date + category, row headers, b-tree slack).
SQLITE_ROW_OVERHEAD = 120  # bytes/row, empirical rough figure
SQLITE_BASE = 28 * 1024     # base file + schema pages


def avg_event_bytes() -> int:
    row = SAMPLE.to_row()
    return len(json.dumps(row, ensure_ascii=False, default=str).encode("utf-8"))


def main():
    per_event = avg_event_bytes()
    print("=" * 64)
    print("STORAGE ESTIMATE — June 2026 events (pre-collection)")
    print("=" * 64)
    print(f"Representative serialized event size: {per_event} bytes")
    print(f"Assumed SQLite per-row overhead:      {SQLITE_ROW_OVERHEAD} bytes")
    print(f"Assumed SQLite base/schema size:      {SQLITE_BASE} bytes")
    print("-" * 64)
    print(f"{'Cat':>3}  {'Category':35} {'Est. events':>11} {'Est. bytes':>12}")
    print("-" * 64)
    total_events = 0
    total_bytes = SQLITE_BASE
    for cid, name in CATEGORIES.items():
        n = EXPECTED_COUNTS.get(cid, 0)
        b = n * (per_event + SQLITE_ROW_OVERHEAD)
        total_events += n
        total_bytes += b
        print(f"{cid:>3}  {name:35} {n:>11} {b:>11,} B")
    print("-" * 64)
    print(f"{'':>3}  {'TOTAL (incl. base/overhead)':35} {total_events:>11} "
          f"{total_bytes:>11,} B")
    print(f"{'':>40}{'':>11}  ≈ {total_bytes/1024:,.1f} KiB "
          f"({total_bytes/1024/1024:.3f} MiB)")
    print("=" * 64)
    print("Note: this is a planning estimate. Run collect.py then report.py for the "
          "ACTUAL on-disk size.")


if __name__ == "__main__":
    main()
