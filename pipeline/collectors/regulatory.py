"""Category 6 — Regulatory, Legal & Approval Events.

Live sources:
- openFDA drugsfda API — free, no key (rate-limited to 240 req/min, 1000/day
  without a key; HttpClient records any 429s).
- Tier 2 FTS: filings that mention future FDA decisions & PDUFA dates.
"""
from __future__ import annotations

from collectors.base import BaseCollector
from models import Event
import edgar_fts

# Tier 2: filings routinely announce a future FDA action date months ahead.
FTS_PDUFA_PHRASES = ["PDUFA date of June", "target action date of June"]

OPENFDA = (
    "https://api.fda.gov/drug/drugsfda.json"
    "?search=submissions.submission_status_date:[20260601+TO+20260630]&limit=50"
)


class RegulatoryCollector(BaseCollector):
    source = "openfda"
    source_type = "api"
    category_id = 6
    rate_delay = 0.5

    def fetch(self) -> list[Event]:
        events: list[Event] = []
        data = self.http.get_json(OPENFDA, respect_robots=False)
        if data and "results" in data:
            for r in data["results"]:
                sponsor = r.get("sponsor_name", "")
                appno = r.get("application_number", "")
                products = r.get("products", [])
                brand = products[0].get("brand_name", "") if products else ""
                for sub in r.get("submissions", []):
                    date_raw = sub.get("submission_status_date", "")
                    if len(date_raw) == 8:
                        date = f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:]}"
                    else:
                        continue
                    if not self.in_window(date):
                        continue
                    events.append(Event(
                        category_id=6,
                        title=f"FDA action: {brand or appno} ({sub.get('submission_status','')})",
                        description=f"{sponsor} — {sub.get('submission_type','')} "
                                    f"{sub.get('submission_number','')}",
                        event_date=date, entity=sponsor or "FDA",
                        importance="medium", source=self.source, source_type="api",
                        native_id=f"{appno}-{sub.get('submission_type')}-{sub.get('submission_number')}",
                        source_url="https://www.accessdata.fda.gov/scripts/cder/daf/",
                        raw={"application_number": appno, "brand": brand},
                    ))
            self.report.notes.append(
                f"openFDA returned {data.get('meta',{}).get('results',{}).get('total','?')} "
                "total matching records")
        else:
            self.report.notes.append(
                "openFDA returned no in-window approvals (forward PDUFA dates are not "
                "published via API); relying on Tier-2 SEC full-text PDUFA mining")

        # --- Tier 2: forward PDUFA / action dates mined from already-filed documents ---
        events.extend(self._fts_forward_pdufa())

        return events

    def _fts_forward_pdufa(self) -> list[Event]:
        out: list[Event] = []
        seen: set[str] = set()
        found = 0
        for phrase in FTS_PDUFA_PHRASES:
            kw = "PDUFA" if "PDUFA" in phrase else "action date"
            hits = edgar_fts.search(self.http, phrase, forms="8-K",
                                    startdt="2025-09-01", enddt="2026-05-31", limit=8)
            for h in hits:
                if h["adsh"] in seen:
                    continue
                seen.add(h["adsh"])
                date = edgar_fts.extract_event_date(
                    self.http, h["url"], keyword=kw, year=2026, month=6)
                if not date:
                    continue
                co = h["company"] or h["ticker"] or "Sponsor"
                key = f"{(h['ticker'] or co).upper()}-{date}"
                if key in seen:
                    continue
                seen.add(key)
                out.append(Event(
                    category_id=6,
                    title=f"{co}: FDA action date (PDUFA) — announced in SEC filing",
                    description=f"Forward PDUFA/target-action date mined from an 8-K "
                                f"filed {h['file_date']} (phrase: \"{phrase}\").",
                    event_date=date, entity=co, importance="high",
                    source="sec_edgar_fts", source_type="api",
                    native_id=f"fts-pdufa-{key}", source_url=h["url"],
                    pub_date=h.get("pub_date"), pub_source=h.get("pub_source"),
                    raw={"phrase": phrase, "filed": h["file_date"], "ticker": h["ticker"]},
                ))
                found += 1
        self.report.notes.append(
            f"SEC full-text search (Tier 2) mined {found} forward PDUFA/action dates "
            f"using phrases {FTS_PDUFA_PHRASES}")
        return out
