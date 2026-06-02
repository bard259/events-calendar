"""Category 3 — Corporate Financial Events.

Live sources:
- SEC EDGAR submissions API (data.sec.gov) — free, no key, but the SEC fair-access
  policy REQUIRES a descriptive User-Agent with contact info (a ToS condition
  HttpClient satisfies).
- Tier 2 FTS: filings that mention future June earnings (via edgar_fts.sec.gov).
"""
from __future__ import annotations

from collectors.base import BaseCollector
from models import Event
import edgar_fts

SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik:010d}.json"

# Tier 2: phrases that, in already-filed documents, announce a FUTURE June earnings event.
FTS_EARNINGS_PHRASES = ["results on June", "conference call on June", "earnings on June"]

# Large-cap basket — material 8-K / earnings-related filings are worth surfacing.
BASKET = {
    320193: "Apple Inc.", 789019: "Microsoft Corp.", 1018724: "Amazon.com Inc.",
    1652044: "Alphabet Inc.", 1045810: "NVIDIA Corp.", 1326801: "Meta Platforms",
    1318605: "Tesla Inc.", 200406: "Johnson & Johnson", 19617: "JPMorgan Chase",
}
# Forms that typically carry a financial event.
MATERIAL_FORMS = {"8-K", "10-Q", "10-K", "8-K/A"}



class CorporateFinancialCollector(BaseCollector):
    source = "sec_edgar"
    source_type = "api"
    category_id = 3
    rate_delay = 0.4  # SEC asks <= ~10 req/s; we stay well under

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        for cik, name in BASKET.items():
            # API source: SEC fair-access ToS honored via declared User-Agent + rate limit
            data = self.http.get_json(SUBMISSIONS.format(cik=cik), respect_robots=False)
            if not data:
                continue
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            descs = recent.get("primaryDocDescription", [])
            accns = recent.get("accessionNumber", [])
            for i, form in enumerate(forms):
                date = dates[i] if i < len(dates) else ""
                if form in MATERIAL_FORMS and self.in_window(date):
                    desc = descs[i] if i < len(descs) else form
                    accn = accns[i] if i < len(accns) else f"{cik}-{i}"
                    events.append(Event(
                        category_id=3,
                        title=f"{name}: {form} filing",
                        description=(desc or form),
                        event_date=date,
                        entity=name,
                        importance="high" if form == "8-K" else "medium",
                        source=self.source, source_type="api",
                        native_id=accn,
                        source_url=f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}",
                        raw={"form": form, "cik": cik},
                    ))
        self.report.notes.append(
            f"EDGAR scanned {len(BASKET)} large-cap issuers for in-window filings")

        # --- Tier 2: forward earnings dates mined from already-filed documents ---
        events.extend(self._fts_forward_earnings())

        return events

    def _fts_forward_earnings(self) -> list[Event]:
        """Find filings (filed Jan–May 2026) that announce a June-2026 earnings event."""
        out: list[Event] = []
        seen: set[str] = set()
        found = 0
        for phrase in FTS_EARNINGS_PHRASES:
            hits = edgar_fts.search(self.http, phrase, forms="8-K",
                                    startdt="2026-01-01", enddt="2026-05-31", limit=8)
            for h in hits:
                if h["adsh"] in seen:
                    continue
                seen.add(h["adsh"])
                date = edgar_fts.extract_event_date(
                    self.http, h["url"], keyword="June", year=2026, month=6)
                if not date:
                    continue
                co = h["company"] or h["ticker"] or "Issuer"
                # Collapse multiple filings about the SAME company+date into one event.
                key = f"{(h['ticker'] or co).upper()}-{date}"
                if key in seen:
                    continue
                seen.add(key)
                out.append(Event(
                    category_id=3,
                    title=f"{co}: earnings / results (announced in SEC filing)",
                    description=f"Forward earnings date mined from an 8-K filed "
                                f"{h['file_date']} (phrase: \"{phrase}\").",
                    event_date=date, entity=co, importance="high",
                    source="sec_edgar_fts", source_type="api",
                    native_id=f"fts-earn-{key}", source_url=h["url"],
                    pub_date=h.get("pub_date"), pub_source=h.get("pub_source"),
                    raw={"phrase": phrase, "filed": h["file_date"], "ticker": h["ticker"]},
                ))
                found += 1
        self.report.notes.append(
            f"SEC full-text search (Tier 2) mined {found} forward earnings dates "
            f"from filings using phrases {FTS_EARNINGS_PHRASES}")
        return out
