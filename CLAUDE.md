# Events — Jun–Dec 2026 Event Collection Pipeline + Calendar App

> New here? Read **`TAKEOVER.md`** first (cold-start onboarding + current state), then this
> file for the deeper conventions.

This repo has two halves:

1. **`pipeline/`** — a Python (stdlib-only) data-collection pipeline that gathers financial /
   macro / geopolitical / **AI-ecosystem** *events* for **June–December 2026** across **9
   categories**, stores them in **SQLite**, runs a **rules-based stock-impact analysis**, and
   reports an **estimated vs. actual** storage footprint. It mixes **live free APIs** and
   **scrapers**, and explicitly **detects, records, and reports** rate-limiting and
   Terms-of-Service issues. **All event data is live-sourced** (`source_type` ∈ {`api`,
   `scraper`}); there is **no synthetic/curated** event data — do not reintroduce `CURATED`
   lists.
2. **`app/`** — an **Expo / React Native** app (runs on **web + iOS** from one codebase) with
   **Month / Week / Day / Latest** views, category filters, and search. Tapping a day shows
   that day's events **and** the stocks likely impacted (ticker, direction, confidence, reason).

## Event categories (stable IDs — used in DB and app filters)

| id | category                          | primary source(s)                                  |
| -: | --------------------------------- | -------------------------------------------------- |
| 1  | Macro & Economic Data             | **T1** parse BLS + BEA published schedules         |
| 2  | Central Bank & Policy             | **T1** parse Fed FOMC calendar + **T3** intl. news |
| 3  | Corporate Financial Events        | SEC EDGAR API + **T2** SEC full-text + **IPOs**    |
| 4  | Corporate Strategic Catalysts     | **T3** Google News RSS + official-site scrape      |
| 5  | Operational Milestones            | Launch Library 2 API (live)                        |
| 6  | Regulatory, Legal & Approval      | openFDA API + **T2** SEC full-text (PDUFA)         |
| 7  | Industry & Supply-Demand          | **T1** parse EIA schedule + **T3** OPEC/shipping news |
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

# 2a. full single-month sweep (all 14 ALL_COLLECTORS) → events.db
python3 pipeline/collect.py --month 2026-06

# 2b. incremental, idempotent, whole Jun–Dec range (run daily; auto re-exports JSON)
python3 pipeline/daily_update.py
python3 pipeline/daily_update.py --start 2026-06-01 --end 2026-12-31

# 3. print the actual storage + rate-limit/ToS report
python3 pipeline/report.py

# 4. rebuild the app's data after any manual DB change
python3 pipeline/export_for_app.py

# app (web)
cd app && npm install && npx expo start --web
# app (iOS) — needs Expo Go or a dev build
cd app && npx expo start --ios
```

## Data flow

`collect.py` (one month, all collectors) **or** `daily_update.py` (incremental, full range)
→ runs each collector → `Event`s → `db.upsert_events()` (dedup by `uid`) → `events.db`
→ `analysis/stock_impact.analyze_all()` → `event_stock_impacts` → `export_for_app.py`
→ `app/assets/events.json`. Each collector also writes a `collector_reports` row
(counts, rate-limit/ToS flags, errors); `report.py` reads `collection_runs` +
`collector_reports` and prints the storage + issues report.

`export_for_app.py` also computes `company_intro` for nfin/Nasdaq API earnings rows from
the preserved `raw_json.nfin_row` ticker/name/market-cap/fiscal-quarter/estimate fields.
That intro is shown on `EventCard` and included in search; it is export-derived metadata,
not a curated/synthetic event source, and `raw_json` is not written to the app payload.

## Notes for future edits

- Keep category IDs 1–9 stable; the app's filter chips and the DB both depend on them.
  Adding a category means updating `config.py:CATEGORIES`/`EXPECTED_COUNTS` **and** the
  app's `src/theme.js` (`categoryColors`/`categoryIcons`). No DB migration is needed
  (the `category` column is derived from `config.CATEGORIES` at insert time).
- The app reads data via `app/assets/events.json`, which is exported from SQLite by
  `pipeline/export_for_app.py`. Re-run that after re-collecting (`daily_update.py` does it
  automatically).
- When adding a collector, register it in `collectors/__init__.py:ALL_COLLECTORS` (picked up
  by `collect.py`) and/or `daily_update.py:DAILY_COLLECTORS` (the daily incremental run).
- **No synthetic event data.** `source_type` is `api` | `scraper` only for events; the
  `synthetic` enum value exists but is unused. Earlier `CURATED = [...]` fallbacks were
  removed from `corporate_financial.py`, `operational.py`, `regulatory.py` — don't add them
  back; surface a real source or skip.
- **Stock-impact engine** (`analysis/stock_impact.py`): entity-match → keyword-rule →
  category-default layers. Entity match is substring-based, so avoid short fragile keys
  (`"arm holdings"` not `"arm"`). Private AI labs (no ticker) map to a public enabler basket.
- **Setup-signals layer** (`analysis/setup_signals.py`): scores earnings/catalyst events for
  VSCO/VSXY-style asymmetry (short interest + activist + analyst-trend + catalyst type →
  0–100 `event_setups` row, surfaced as a ⚡ SETUP badge). `SETUP_PROFILES` is a **sourced,
  dated snapshot** (analytical reference, not event data) — refresh periodically; a live
  activist refresher via EDGAR FTS exists (`verify_activist_edgar`, off by default). Runs in
  `collect.py`/`daily_update.py`; standalone `enrich_setups.py`.
- **Earnings-preview layer** (`analysis/earnings_preview.py`): per-ticker `PREVIEWS` (sourced,
  dated) attach a consensus bar / options-implied move / directional lean / bull-bear-watch to
  marquee earnings events → `event_previews` table → `ev.preview` → 📊 block in the day-detail.
  Earnings-keyword-gated. Same refresh discipline as setups. Research, not advice.
- **Multi-month dates**: `parsers.extract_dates_window(text, start_iso, end_iso)` is the
  range-aware extractor used by the daily/AI collectors; `extract_dates(text, year, month)`
  is the single-month one. Both keep the `(?!\d)` "June 2026"≠"June 20" guard.
- **Company cards** (`company_cards.py` → `company_cards` table → `app/assets/company_cards.json`):
  one card per ticker with a business intro — curated `company_tldr.COMPANY_TLDR` > SEC SIC
  industry (cached in `memory/sic_cache.json`, capped per run) > `{size}-cap` fallback. Events
  carry `company_ticker`; the app links the card via a tappable "About ›" → `CompanyModal`.
- **Decision/critic agents** (`decision_agents.py`, `run_daily_agents.py`): rules-based paper
  decisions from `event_previews` + a learnable `memory/key_knowledge_memory.json`; price
  snapshots (`investment_price_snapshots`); critic updates memory. Reports in `pipeline/reports/`,
  surfaced in the app's **Reports** tab (`export_agent_reports.py` → `agent_reports.json`).
- **Earnings-alpha (continuous learning)** (`analysis/earnings_alpha.py`): per-earnings
  `pop_score` (post-earnings *increase* likelihood) + research-grounded `lookahead_days`
  (pre-earnings-drift entry timing) → `earnings_alpha` table, merged into `ev.preview`.
  `evaluate_outcomes` reads price snapshots for realized pre→post returns (`earnings_outcomes`);
  `learn` self-tunes thresholds + per-tier look-ahead in `memory/earnings_alpha_params.json`.
  Runs in `run_daily_agents.py`.
