"""SEC EDGAR full-text search (efts.sec.gov) — Tier 2 forward-date mining.

Past, already-filed documents routinely *announce* future-dated events ("PDUFA date of
June 8, 2026", "will report results on June 25, 2026"). The submissions API only lists
filings (and is backward-looking), but full-text search finds these forward mentions.
We then fetch each candidate document and extract the in-window date near the keyword.
"""
from __future__ import annotations

import re
from urllib.parse import quote

from parsers import extract_dates, strip_tags

FTS_URL = "https://efts.sec.gov/LATEST/search-index?q={q}&forms={forms}&startdt={s}&enddt={e}"


def search(http, phrase: str, forms: str, startdt: str, enddt: str, limit: int = 10):
    """Return up to `limit` FTS hits as dicts: {company, ticker, cik, adsh, doc, date, url}."""
    url = FTS_URL.format(q=quote(f'"{phrase}"'), forms=forms, s=startdt, e=enddt)
    data = http.get_json(url, respect_robots=False)
    out = []
    if not data:
        return out
    for h in data.get("hits", {}).get("hits", [])[:limit]:
        src = h.get("_source", {})
        _id = h.get("_id", "")
        adsh, _, doc = _id.partition(":")
        ciks = src.get("ciks", [])
        cik = ciks[0].lstrip("0") if ciks else ""
        names = src.get("display_names", [])
        name = names[0] if names else ""
        ticker = ""
        mt = re.search(r"\(([A-Z.]{1,6})\)", name)
        if mt:
            ticker = mt.group(1)
        company = re.sub(r"\s*\(.*", "", name).strip()
        doc_url = (f"https://www.sec.gov/Archives/edgar/data/"
                   f"{cik}/{adsh.replace('-', '')}/{doc}") if cik and doc else ""
        out.append({"company": company, "ticker": ticker, "cik": cik, "adsh": adsh,
                    "doc": doc, "file_date": src.get("file_date", ""), "url": doc_url,
                    # pub_date = when SEC received the filing; pub_source = SEC EDGAR
                    "pub_date": src.get("file_date", ""), "pub_source": "SEC EDGAR"})
    return out


def extract_event_date(http, doc_url: str, keyword: str, year: int, month: int) -> str | None:
    """Fetch a filing doc and return the in-window date nearest the keyword, if any."""
    if not doc_url:
        return None
    html = http.get(doc_url, respect_robots=False)
    if not html:
        return None
    text = strip_tags(html)
    # Look at windows of text around each keyword occurrence first (higher precision).
    for m in re.finditer(re.escape(keyword), text, flags=re.I):
        ctx = text[m.start(): m.start() + 220]
        ds = extract_dates(ctx, year, month)
        if ds:
            return ds[0]
    # Fallback: any in-window date anywhere in the doc.
    ds = extract_dates(text, year, month)
    return ds[0] if ds else None
