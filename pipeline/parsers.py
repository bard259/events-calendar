"""Shared HTML / date parsing helpers for the historical-document collectors.

These turn already-published pages (Fed calendar, BLS schedule) and free-text
(filings, news headlines) into in-window ISO dates. Kept conservative: when a precise
day cannot be extracted, callers should skip rather than guess.
"""
from __future__ import annotations

import calendar
import html as _html
import re

MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}
MONTHS.update({m.lower(): i for i, m in enumerate(calendar.month_abbr) if m})


def strip_tags(text: str) -> str:
    # Unescape first so entity-encoded markup (e.g. RSS "&lt;a href=...&gt;") becomes real
    # tags, then strip. Run a second unescape pass for any double-encoded entities.
    text = _html.unescape(text)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def extract_dates(text: str, year: int, month: int) -> list[str]:
    """Return sorted unique ISO dates for `month`/`year` mentioned in `text`.

    Handles "June 16, 2026", "June 16", "16-17" ranges following a month name,
    and "06/16/2026". Only days valid for the month are returned.
    """
    mname = calendar.month_name[month].lower()
    last_day = calendar.monthrange(year, month)[1]
    found: set[int] = set()

    def add(g):
        if g and g.isdigit() and 1 <= int(g) <= last_day:
            found.add(int(g))

    # "June 16, 2026" / "June 16" / "June 16-17". The (?!\d) stops "June 2026" being
    # misread as "June 20" (grabbing the leading digits of the year).
    for m in re.finditer(
        rf"{mname}\s+(\d{{1,2}})(?!\d)(?:\s*[-–]\s*(\d{{1,2}})(?!\d))?(?:,?\s*{year})?",
        text, flags=re.I,
    ):
        add(m.group(1))
        add(m.group(2))

    # Day-before-month: "16 June 2026" / "5 June" (common international style)
    for m in re.finditer(rf"\b(\d{{1,2}})\s+{mname}(?:\s+{year})?\b", text, flags=re.I):
        add(m.group(1))

    # "06/16/2026" or "6/16/26"
    for m in re.finditer(rf"\b0?{month}/(\d{{1,2}})/(?:{year}|{year % 100})\b", text):
        add(m.group(1))

    return [f"{year}-{month:02d}-{d:02d}" for d in sorted(found)]


def extract_dates_window(text: str, start_iso: str, end_iso: str) -> list[str]:
    """Return sorted unique ISO dates found in `text` that fall within [start_iso, end_iso].

    Scans every (year, month) the window spans and reuses `extract_dates`, so it inherits
    the same robust patterns ("June 16, 2026", "16 June 2026", "06/16/2026") and the
    "June 2026"-not-"June 20" guard. Used by the multi-month daily news collector.
    """
    sy, sm = int(start_iso[:4]), int(start_iso[5:7])
    ey, em = int(end_iso[:4]), int(end_iso[5:7])
    out: list[str] = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        for iso in extract_dates(text, y, m):
            if start_iso <= iso <= end_iso:
                out.append(iso)
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return sorted(set(out))


def first_date(text: str, year: int, month: int) -> str | None:
    ds = extract_dates(text, year, month)
    return ds[0] if ds else None


def parse_time_to_iso(date_iso: str, time_str: str) -> str | None:
    """'10:00 AM' + '2026-06-02' -> '2026-06-02T10:00:00' (best effort, ET-naive)."""
    m = re.match(r"(\d{1,2}):(\d{2})\s*([AP]M)", time_str.strip(), re.I)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3).upper()
    if ap == "PM" and h != 12:
        h += 12
    if ap == "AM" and h == 12:
        h = 0
    return f"{date_iso}T{h:02d}:{mi:02d}:00"
