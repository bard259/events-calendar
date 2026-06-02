# Events — June 2026 Event Collection Pipeline + Calendar App

This repo has two halves:

1. **`pipeline/`** — a Python data-collection pipeline that gathers financial / macro /
   geopolitical *events* for **June 2026** across 8 categories, stores them in **SQLite**,
   and reports an **estimated vs. actual** storage footprint. It mixes **live free APIs**
   and **scrapers**, and explicitly **detects, records, and reports** rate-limiting and
   Terms-of-Service issues.
2. **`app/`** — an **Expo / React Native** app (runs on **web + iOS** from one codebase)
   with a clickable **calendar UI**. Tapping a day shows that day's collected events.

## Event categories (stable IDs — used in DB and app filters)

| id | category                          | primary source(s)                                  |
| -: | --------------------------------- | -------------------------------------------------- |
| 1  | Macro & Economic Data             | **T1** parse BLS published schedule + curated      |
| 2  | Central Bank & Policy             | **T1** parse Fed FOMC calendar + curated intl.     |
| 3  | Corporate Financial Events        | SEC EDGAR API + **T2** SEC full-text + **IPOs** + curated |
| 4  | Corporate Strategic Catalysts     | curated + **T3** Google News RSS mining            |
| 5  | Operational Milestones            | Launch Library 2 API (live)                        |
| 6  | Regulatory, Legal & Approval      | openFDA API + **T2** SEC full-text (PDUFA) + curated |
| 7  | Industry & Supply-Demand          | OPEC / conference calendar (curated)               |
| 8  | Geopolitical & Security           | curated + **T3** Google News RSS mining            |
| 9  | AI & Compute Ecosystem            | **T3** Google News RSS mining (`collectors/ai_industry.py`) |

### Forward-date mining tiers (events knowable today from already-published docs)

- **Tier 1 — structured published calendars** (`parsers.py`): the Fed and BLS publish
  forward schedules; we *parse* the pages (`central_bank.py`, `macro.py`) instead of
  curating. High confidence.
- **Tier 2 — SEC full-text search** (`edgar_fts.py`): already-filed 8-Ks announce future
  earnings ("results on June…") and FDA dates ("PDUFA date of June…"). We search
  `efts.sec.gov`, fetch each hit's document, and extract the in-window date near the
  keyword. Deduped by company+date. Medium-high confidence.
- **Tier 3 — news/press mining** (`collectors/news.py`): Google News RSS. NOISY by design
  — only emits when a precise June-2026 date is extractable, tagged `importance=low`.
  Treat as leads, not confirmed events.

### Categorization rules (where ambiguous event types go)

- **IPOs / going-public events → category 3** (capital-markets / corporate financial).
  Collected in `collectors/ipo.py`: `IpoEdgarCollector` scrapes real dated IPOs from SEC
  EDGAR (424B4 pricings + S-1 registrations, filtered on "initial public offering");
  `IpoNewsCollector` mines marquee *rumored* IPOs of still-private issuers (e.g. SpaceX,
  Stripe) from Google News and only emits them when a concrete June date is reported.
- **M&A / restructuring / product launches → category 4** (strategic catalysts).
- **AI / compute-ecosystem milestones → category 9.** `collectors/ai_industry.py`
  news-mines the AI build-out — chipmakers (Nvidia, AMD, Micron, Broadcom, TSMC),
  frontier labs (Anthropic, OpenAI, xAI — private), hyperscalers (Microsoft, Google,
  Amazon, Oracle, CoreWeave) and the infrastructure contractors that supply them
  (Super Micro, Dell, Vertiv, Arista, SK Hynix, Foxconn). It detects which roster
  company a headline is about and sets it as the event `entity`, so the stock-impact
  engine attaches the right ticker. A private lab (no ticker) maps to its public
  enablers via a keyword rule (e.g. "Anthropic" → NVDA/AMZN/GOOGL/MSFT). The generic
  AI query was removed from category 4 to avoid cross-lane duplication. An entity-less
  headline must hit an AI/compute keyword (`_AI_TERMS`) to be kept (noise gate).
- A still-private issuer's IPO will NOT appear in EDGAR (no filings yet); it only surfaces
  via the news collector once a date is reported. EDGAR in-window IPO pricings are sparse
  early in the month and fill in as 424B4s are filed.

## Conventions

- **No heavy third-party deps in the pipeline.** Uses Python stdlib only (`urllib`,
  `sqlite3`, `html.parser`). Keeps it runnable anywhere with `python3 pipeline/collect.py`.
- Every collector subclasses `collectors.base.BaseCollector` and returns `Event` objects.
- HTTP goes through `http_client.HttpClient`, which records request counts, HTTP 429/403,
  `Retry-After`, and `robots.txt` / required-User-Agent (ToS) signals into the run report.
- `source_type` is one of `api` | `scraper` | `synthetic`. Synthetic data is realistic and
  clearly labeled so it is never confused with collected data.
- Dedup key is `uid = f"{source}:{native_id}"`. For mined events (Tier 2/3), `native_id`
  encodes company+date (not the filing id) so multiple docs about the same real-world
  event collapse into one row.
- `parsers.py:extract_dates()` is the shared forward-date extractor — note its `(?!\d)`
  guard so "June 2026" is NOT misread as "June 20". It also handles "5 June 2026" and
  "06/16/2026". Add test cases there if you extend it.

## Common commands

```bash
# 1. estimate storage BEFORE collecting
python3 pipeline/estimate_storage.py

# 2. run the full collection (writes pipeline/events.db)
python3 pipeline/collect.py --month 2026-06

# 3. print the actual storage + rate-limit/ToS report
python3 pipeline/report.py

# app (web)
cd app && npm install && npx expo start --web
# app (iOS) — needs Expo Go or a dev build
cd app && npx expo start --ios
```

## Data flow

`collect.py` → runs each collector → `Event`s → `db.upsert_events()` → `events.db`.
Each collector also writes a `collector_reports` row (counts, rate-limit/ToS flags, errors).
`report.py` reads `collection_runs` + `collector_reports` and prints the storage + issues report.

## Notes for future edits

- Keep category IDs 1–9 stable; the app's filter chips and the DB both depend on them.
  Adding a category means updating `config.py:CATEGORIES`/`EXPECTED_COUNTS` **and** the
  app's `src/theme.js` (`categoryColors`/`categoryIcons`). No DB migration is needed
  (the `category` column is derived from `config.CATEGORIES` at insert time).
- The app reads data via `app/assets/events.json`, which is exported from SQLite by
  `pipeline/export_for_app.py`. Re-run that after re-collecting.
- When adding a collector, register it in `collectors/__init__.py:ALL_COLLECTORS`.
