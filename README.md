# Events — June 2026 Event Pipeline + Calendar App

Two components:

1. **`pipeline/`** — Python (stdlib-only) data-collection pipeline that gathers events
   across **8 categories** for **June 2026**, stores them in **SQLite**, and reports an
   **estimated vs. actual** storage footprint. It mixes **live free APIs** and **scrapers**,
   and **detects / records / reports** rate-limit and Terms-of-Service issues.
2. **`app/`** — **Expo / React Native** app (one codebase → **web + iOS**) with a clickable
   **calendar UI**: tap a day to see that day's collected events.

## Quick start

```bash
# --- pipeline (no pip install needed) ---
python3 pipeline/estimate_storage.py      # storage ESTIMATE (before collecting)
python3 pipeline/collect.py --month 2026-06   # collect -> pipeline/events.db
python3 pipeline/report.py                 # ACTUAL storage + rate-limit/ToS report
python3 pipeline/export_for_app.py         # export -> app/assets/events.json

# --- app ---
cd app && npm install
npx expo start --web     # website
npx expo start --ios     # iOS (Expo Go or a dev build)
```

## Categories & sources

| id | Category                          | How it's collected                                              |
| -: | --------------------------------- | --------------------------------------------------------------- |
| 1  | Macro & Economic Data             | **T1 parse** BLS published schedule + curated non-BLS releases  |
| 2  | Central Bank & Policy             | **T1 parse** Federal Reserve FOMC calendar + curated intl. CBs  |
| 3  | Corporate Financial Events        | **live API** (SEC EDGAR) + **T2** SEC full-text + **IPOs** + curated |
| 4  | Corporate Strategic Catalysts     | curated + **T3** Google News RSS mining                         |
| 5  | Operational Milestones            | **live API** (Launch Library 2) + curated                       |
| 6  | Regulatory, Legal & Approval      | **live API** (openFDA) + **T2** SEC full-text PDUFA + curated   |
| 7  | Industry & Supply-Demand          | curated (OPEC, conferences, contract pricing)                   |
| 8  | Geopolitical & Security           | curated + **T3** Google News RSS mining                         |

### Forward-date mining (the key idea)

Most "future" June-2026 events are already documented in **published** material today:

- **Tier 1 — published calendars:** the Fed and BLS publish their schedules a year ahead;
  we parse those pages directly (`parsers.py`, `collectors/central_bank.py`, `macro.py`).
- **Tier 2 — SEC full-text search** (`edgar_fts.py`): already-filed 8-Ks announce forward
  **earnings** and **PDUFA / FDA action dates**. We query `efts.sec.gov`, fetch each
  candidate filing, and extract the June date near the keyword. Recent runs surfaced real
  PDUFA dates (Arvinas, Merck, Ionis, …) and forward earnings (Victoria's Secret, Greif, …).
- **Tier 3 — news mining** (`collectors/news.py`): Google News RSS. Noisy by design —
  only emits when a precise date is extractable, tagged `importance=low` (leads, not facts).

**IPOs** (`collectors/ipo.py`, category 3): real dated IPOs are scraped from SEC EDGAR
(424B4 pricings + S-1 registrations filtered to genuine IPOs). Marquee *rumored* IPOs of
still-private companies — e.g. **SpaceX** — aren't in EDGAR yet, so they're mined from
news and placed on the calendar once a date is reported (SpaceX → June 12 in the current
data). EDGAR in-window pricings are sparse at the very start of the month and fill in as
424B4s are filed.

`source_type` on every event is `api` | `scraper` | `synthetic`, so collected data is
never confused with curated data. The app surfaces this tag on each event card.

## Storage: estimate vs. actual (latest run)

| Metric                         | Value                          |
| ------------------------------ | ------------------------------ |
| Pre-collection **estimate**    | ~276 KiB (282,272 bytes)       |
| **Actual** SQLite file         | **92 KiB (94,208 bytes)**      |
| Logical text payload           | ~28 KiB (29,033 bytes)         |
| Events collected               | 114                            |
| Avg bytes/event (file)         | ~826 B                         |

The estimate intentionally over-provisions (it budgets ~120 large-cap earnings for cat 3
and more launches than the month actually has), so the real DB lands ~67% under estimate.
`report.py` prints the per-category breakdown and the exact delta. (Numbers move run to
run as live APIs and full-text search return more data closer to / during the month.)

## Rate-limit / ToS handling

`pipeline/http_client.py` records, per collector:
- HTTP request counts,
- **HTTP 429** (with `Retry-After`) → flagged as rate-limited,
- **HTTP 403 / 401** → flagged as a ToS / access-policy / auth-required issue,
- **robots.txt** — fetched with the declared User-Agent; an explicit `Disallow` is obeyed
  and recorded. (API endpoints honor their own ToS via a declared User-Agent + rate
  limiting rather than robots.txt — see notes in the code.)

All of this is written to the `collector_reports` table and printed by `report.py`.

## Re-running

Re-running `collect.py` is idempotent (events dedupe by `uid`). Delete `pipeline/events.db`
to start fresh. After collecting, run `export_for_app.py` to refresh the app's data.
