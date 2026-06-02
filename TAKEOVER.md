# TAKEOVER — Agent Onboarding & Handoff Manual

> **Purpose.** This file lets a *fresh* agent (or human) take over this project cold —
> no prior conversation context required. Read this top-to-bottom, then `CLAUDE.md`
> for the deeper conventions. Keep this file **updated** at the end of any substantial
> work session (there's a "Session log" at the bottom — append to it).

Last updated: **2026-06-02** · Data span: **2026-06-01 → 2026-12-31** · DB: **174 events**

---

## 0. TL;DR — what this project is

Two halves in one repo:

1. **`pipeline/`** — Python (stdlib only) that collects *forward-looking* financial /
   macro / geopolitical / AI events for **June–December 2026** from **live free APIs +
   scrapers**, stores them in **SQLite** (`pipeline/events.db`), runs a **rules-based
   stock-impact analysis**, and exports `app/assets/events.json`.
2. **`app/`** — an **Expo / React Native** app (web + iOS from one codebase) — a calendar
   with **Month / Week / Day / Latest** views, category filters, search, and a day-detail
   panel that shows each day's events **and** the stocks likely impacted.

**Hard rule (learned the hard way): NO synthetic / curated / hand-typed event data.**
Every event must trace to a live source (`source_type` ∈ {`api`, `scraper`}). The DB
currently has **0 synthetic** rows. Do not reintroduce `CURATED = [...]` lists.

---

## 1. Run it

```bash
# Pipeline (Python 3, no pip installs needed — stdlib only)
python3 pipeline/estimate_storage.py                 # storage estimate (before collecting)
python3 pipeline/collect.py --month 2026-06          # ONE month × all 14 collectors → events.db
python3 pipeline/daily_update.py                     # INCREMENTAL: 3 collectors over full range
python3 pipeline/daily_update.py --start 2026-06-01 --end 2026-12-31
python3 pipeline/report.py                            # storage + rate-limit/ToS report
python3 pipeline/export_for_app.py                   # rebuild app/assets/events.json from DB

# App
cd app && npm install && npx expo start --web        # web
cd app && npx expo start --ios                       # iOS (needs Expo Go / dev build)
```

- **`collect.py`** = full sweep of `collectors/__init__.py:ALL_COLLECTORS` for a **single
  month**. Wipes nothing; `INSERT OR IGNORE` dedups by `uid`.
- **`daily_update.py`** = lightweight **incremental** run of `DAILY_COLLECTORS`
  (`DailyTechNewsCollector`, `OfficialEventsCollector`, `OperationalCollector`) across the
  **whole Jun–Dec range**. Idempotent — safe to run daily (cron / `/schedule`). Only new
  events get added; only new events get stock impacts; then it re-exports the JSON.
- Re-run `export_for_app.py` after any DB change, or the app shows stale data
  (`daily_update.py` already calls it for you).

### Preview / screenshots (for agents using the Claude preview tools)
`.claude/launch.json` runs `expo start --web` on **port 8090** (8081 is often occupied by
stray dev servers; 8090 avoids the non-interactive port-prompt hang). Use
`preview_start` → `preview_eval`/`preview_screenshot`. The Expo **first** web bundle takes
~10–30 s; poll the URL before screenshotting.

---

## 2. Repo map

```
pipeline/
  config.py            categories (1–9), RANGE_START/END, paths, HTTP UA/contact
  models.py            Event + CollectorReport dataclasses; uid = sha1(source:native_id)
  http_client.py       stdlib HTTP; records 429/403, Retry-After, robots.txt / UA (ToS)
  parsers.py           strip_tags(); extract_dates() (single month) + extract_dates_window() (range)
  db.py                SQLite schema + upsert/report/impact helpers (no migrations needed)
  edgar_fts.py         SEC full-text search helper (efts.sec.gov) — Tier 2
  collect.py           orchestrator: ALL_COLLECTORS for one month + stock analysis
  daily_update.py      incremental DAILY_COLLECTORS over the full range
  report.py            reads runs + collector_reports → storage & issue report
  estimate_storage.py  pre-collection size estimate (uses EXPECTED_COUNTS)
  export_for_app.py    DB → app/assets/events.json (events + stock_impacts + setup + categories)
  enrich_setups.py     standalone: recompute event_setups + re-export (no re-collect)
  analysis/
    stock_impact.py    rules engine: ENTITY_TICKERS, SECTOR_ETFS, KEYWORD_RULES, CATEGORY_DEFAULTS
    setup_signals.py   pre-event asymmetry scorer: SETUP_PROFILES (short/activist/analyst) → event_setups
    earnings_preview.py  per-ticker earnings-preview notes (bar/implied move/lean) → event_previews
  collectors/
    __init__.py        ALL_COLLECTORS registry (collect.py uses this)
    base.py            BaseCollector (lifecycle, in_window filter, report wiring)
    news.py            NewsCollector base (Google News RSS) + Strategic/Geopolitical subclasses
    macro.py           cat 1 — BLS + BEA schedule parse (T1) + news (T3)
    central_bank.py    cat 2 — Fed FOMC parse (T1) + ECB/BoE/BoJ news (T3)
    corporate_financial.py  cat 3 — SEC EDGAR submissions API + Tier-2 FTS forward earnings
    corporate_strategic.py  cat 4 — news-mined product/M&A/investor-day (AI query removed)
    operational.py     cat 5 — Launch Library 2 API (rocket launches)
    regulatory.py      cat 6 — openFDA API + Tier-2 FTS PDUFA dates
    industry.py        cat 7 — EIA petroleum schedule parse + OPEC/shipping news
    geopolitical.py    cat 8 — elections/summits/tariffs news
    ipo.py             cat 3 — IpoEdgarCollector (424B4/S-1) + IpoNewsCollector (rumored)
    ai_industry.py     cat 9 — AI & compute ecosystem news mining (chips/models/datacenters)
    daily_news.py      DailyTechNewsCollector — real, dated marquee tech catalysts (multi-cat)
    official_events.py OfficialEventsCollector — scrapes flagship conf dates from official sites
app/
  App.js               header, category chips, Month/Week/Day/Latest switcher, search, nav
  assets/events.json   THE app data (exported from DB) — do not hand-edit
  src/
    data.js            loads events.json; MONTHS, RANGE_START/END, LAST_COLLECTED, searchEvents()
    theme.js           colors, categoryColors[1..9], categoryIcons[1..9], importance/direction cfg
    Calendar.js        month grid (urgency bar, dots, today pill)
    WeekView.js        7-day view
    DayView.js         single-day list
    LatestView.js      "latest identified events" — grouped by collected_at, newest first
    EventCard.js       reusable event card (SourcePill + optional showDate)
    DayDetail.js       modal: Events tab / Stocks tab (aggregates day's impacts)
    StockImpact.js     stock-signal cards (ticker badge ▲▼◆, confidence, reason)
    SearchModal.js     full-text search over title/entity/desc/category/tickers
CLAUDE.md              conventions (READ THIS SECOND)
TAKEOVER.md            this file
```

---

## 3. The 9 categories (stable IDs — DB + app filters depend on them)

| id | category | source |
|---:|----------|--------|
| 1 | Macro & Economic Data | BLS + BEA schedule parse (T1) |
| 2 | Central Bank & Policy | Fed FOMC parse (T1) + intl news (T3) |
| 3 | Corporate Financial | SEC EDGAR API + Tier-2 FTS + IPOs |
| 4 | Corporate Strategic Catalysts | news mining (T3) + official-site scrape |
| 5 | Operational Milestones | Launch Library 2 API |
| 6 | Regulatory/Legal/Approval | openFDA API + Tier-2 FTS PDUFA |
| 7 | Industry & Supply-Demand | EIA parse + OPEC/shipping news |
| 8 | Geopolitical & Security | elections/summits/tariffs news |
| 9 | **AI & Compute Ecosystem** | AI news mining + official conf scrape |

**Adding a category** = update `config.py:CATEGORIES` **and** `EXPECTED_COUNTS` **and**
`app/src/theme.js` (`categoryColors`/`categoryIcons`). No DB migration (the `category`
text column is derived from `config.CATEGORIES` at insert time). Keep IDs 1–9 stable.

### Forward-date mining tiers
- **T1 structured calendars** (`parsers.py` + `macro.py`/`central_bank.py`): parse Fed/BLS
  published schedules. High confidence.
- **T2 SEC full-text** (`edgar_fts.py`): already-filed 8-Ks announce future earnings
  ("results on June…") / PDUFA dates. Deduped by company+date. Medium-high.
- **T3 news mining** (`news.py`, `ai_industry.py`, `daily_news.py`): Google News RSS.
  Noisy — only emits when a precise in-window date is extractable. Treat as leads.

---

## 4. Stock-impact engine (`analysis/stock_impact.py`)

Pure stdlib, no API keys. For each event, three layers (deduped by ticker, cap 12):
1. **Entity match** — company name in blob → that ticker, `high` confidence.
2. **Keyword rules** — `KEYWORD_RULES` regexes → sector ETFs / tickers with direction + reason.
3. **Category default** — `CATEGORY_DEFAULTS[cat]` baseline (fills gaps).

`direction`: `+1` positive / `-1` negative / `0` watch. Output per impact:
`{ticker, direction, confidence, reason (≤120 chars), sector}` → `event_stock_impacts` table.

**Gotcha — substring matching in Layer 1.** Entity match uses `fragment in blob`, so
short keys are dangerous: `"arm"` matches "pharma"/"alarm", `"cisco"` matches "San
Francisco". Use safe keys (`"arm holdings"`, `"cisco systems"`) and make the collector's
canonical `entity` name contain that key. Private labs (Anthropic/OpenAI/xAI) have **no
ticker** → a keyword rule maps them to the public enabler basket (NVDA/AMZN/GOOGL/MSFT).

---

## 5. Conventions & gotchas (the expensive lessons)

- **stdlib only** in the pipeline (`urllib`, `sqlite3`, `html.parser`, `re`). No `requests`,
  no `pip install`. Keeps it runnable anywhere.
- **`source_type`** ∈ {`api`, `scraper`}. `synthetic` exists in the enum but must **not** be
  used for events. (Earlier sessions removed all `CURATED` fallback lists from
  `operational.py`, `regulatory.py`, `corporate_financial.py` — don't add them back.)
- **robots.txt / ToS** (`http_client.py`): APIs are accessed with `respect_robots=False`
  + a descriptive User-Agent (SEC/openFDA/LL2 fair-access). A 403/missing robots.txt is
  treated as *allowed* for APIs. Only HTML scrapers honor robots.txt
  (`respect_robots=True`, e.g. `official_events.py`). 429/403/Retry-After are recorded in
  the run report — **don't silence these**, they're a deliverable.
- **Date extraction** (`parsers.py`): `extract_dates()` has a `(?!\d)` guard so "June 2026"
  is NOT misread as "June 20"; also handles "5 June 2026" and "06/16/2026".
  `extract_dates_window(text, start_iso, end_iso)` is the range-aware version used by the
  multi-month collectors. Add test cases when you extend it.
- **Dedup**: `uid = sha1(f"{source}:{native_id}")`. For **mined** events, `native_id`
  encodes **company+date(+category)** so multiple articles about one real event collapse
  to one row (e.g. `daily_news.py`: `f"{slug(entity)}:{date}:{cat}"`).
- **Noise gates**: news collectors drop items with no in-window date; `ai_industry.py` and
  `daily_news.py` additionally **require a known entity or an AI/compute keyword** so
  off-topic Google News results (horoscopes, sports) don't leak in.
- **Registering a collector**: add it to `collectors/__init__.py:ALL_COLLECTORS` (for
  `collect.py`) and/or `daily_update.py:DAILY_COLLECTORS` (for the daily incremental).
- **App data flow**: SQLite → `export_for_app.py` → `app/assets/events.json` → `data.js`.
  The app reads categories from the export, so a new category appears automatically once
  `theme.js` has its color/icon.

---

## 6. Current state (as of last update)

- **174 events**, span **2026-06-01 → 2026-12-31**. Source split: **137 api / 37 scraper /
  0 synthetic**. Per-category: 1→19, 2→3, 3→30, 4→5, 5→100 (LL2 launches dominate the
  multi-month window), 6→7, 7→3, 8→4, 9→3.
- Category **9 (AI & Compute Ecosystem)** is live: `ai_industry.py` + AI rules in
  `stock_impact.py` + violet `🧠` lane in `theme.js`. (Anthropic/OpenAI etc. map to the
  enabler basket since they're private.)
- App has 4 views (Month/Week/Day/**Latest**) + search + day-detail Events/Stocks tabs.
- Git: single "Initial commit" on disk; current working tree has uncommitted edits — see
  session log. Commit/push only when the user asks.

### Why category-9 / AI counts look small on any given run
T3 news mining only emits when a headline carries a **concrete in-window date**. Google
News surfaces few such AI items at a time, so counts grow as `daily_update.py` runs over
successive days. This is by design, not a bug.

---

## 7. Likely next tasks / open ideas

- Keep running `daily_update.py` (or schedule it) so confirmed events fill in over time.
- Consider adding `ai_industry.py`-style entity rosters to more lanes for richer stock links.
- The cat-6 openFDA note string was corrected ("relying on Tier-2 SEC full-text PDUFA
  mining"); it self-corrects on the next `collect.py`.
- No automated tests yet — `parsers.extract_dates*` is the highest-value place to add them.

---

## 8. Session log (append newest at top)

### 2026-06-02 (latest+1) — earnings-preview annotations (AVGO)
- New **`analysis/earnings_preview.py`** mirrors the setup-signals pattern: a sourced/dated
  `PREVIEWS` table (keyed by ticker) attaches the consensus bar, options-implied move, a
  directional lean, and bull/bear/watch bullets to a marquee earnings event. New DB table
  **`event_previews`** (payload = JSON) + `db.save_previews`; exported as `ev.preview`;
  rendered as a 📊 EARNINGS PREVIEW block in the day-detail (`EarningsPreviewBlock` in
  `EventCard.js`, shown when `detail`). Wired into `collect.py`/`daily_update.py`/`enrich_setups.py`.
- Seeded **AVGO** (Broadcom Q2 FY26, reports 6/3): implied ±8–10.6% (vs ±6.7% avg), EPS
  $2.40 / rev ~$22.1B / AI-semi whisper ~$5B; lean = beat likely but two-sided, sell-the-news
  risk at ATHs. Gated to earnings events only (keyword) so non-earnings Broadcom news won't
  inherit it. Refresh `PREVIEWS` before each print (estimates/implied vol move daily).

### 2026-06-02 (latest) — VSCO→VSXY, setup-signals enrichment, comparables
- **Ticker fix**: `stock_impact.py` `ENTITY_TICKERS` "victoria's secret"→**VSXY** (was VSCO,
  renamed 6/2); added "kohl's"→KSS, "macy's"→M.
- **New pre-event "setup" layer** — `analysis/setup_signals.py`: scores earnings/catalyst
  events for **VSCO-style asymmetry** (short interest + activist + analyst-trend + catalyst
  type → 0–100). Sourced snapshot `SETUP_PROFILES` (VSXY, KSS, M, CTRN) with `as_of` +
  `sources`; live activist refresh via `verify_activist_edgar()` (EDGAR FTS, not run by
  default). New DB table `event_setups` (+ `db.save_setups`); exported per-event as
  `ev.setup`; standalone runner `pipeline/enrich_setups.py`; wired into `collect.py` +
  `daily_update.py` (runs every collection, no network).
- **App**: ⚡ SETUP badge + summary line in shared `EventCard.js` (score ≥45 badges;
  any profiled event shows a muted line); rich detail block (bias, notes, source links)
  in the day-detail via `EventCard … detail`.
- **Daily miner**: added Victoria's Secret / Kohl's / Macy's to `daily_news.py` roster +
  queries so their dated catalysts get mined → auto-badged.
- **Comparables found** (in current calendar): **VSXY 6/2 = 78 High-asymmetry**;
  **CTRN (Citi Trends) 6/2 = 31 Low** (turnaround + ~10% short, no current activist).
  Strong archetypes **KSS / M** are profiled and will badge once a dated earnings event is
  mined (none in the window yet). Reference numbers are dated snapshots — refresh
  `SETUP_PROFILES` periodically (short interest moves).

### 2026-06-02 (later) — docs sync + VSCO research
- Brought the summary docs in line with current state: `CLAUDE.md` (Jun–Dec range, 9
  categories, no-synthetic rule, `daily_update.py`, stock engine, `extract_dates_window`),
  memory `events-project.md`, and the `MEMORY.md` index line. No code/data changes.
- Ad-hoc research (not a project change): Victoria's Secret (VSCO→**VSXY** as of 6/2/2026)
  ~+50% on Q1 print. Leading indicators that foreshadowed it: 4 straight quarters of
  positive comps under CEO Hillary Super; FY25 Q4 beat (3/5/26) + raised FY26 view;
  Barington + BBRC (12.9%) activists + May-2025 poison pill; ~19% of float short (squeeze
  fuel); analysts had lifted targets (~$73→$81) into the print. Beat was huge: adj EPS
  $0.60 vs $0.32 est, rev +15%, op income $80M vs $32–42M guide.

### 2026-06-02 — AI ecosystem lane + latest-page date + this manual
- Added **category 9 (AI & Compute Ecosystem)**: new `collectors/ai_industry.py` (mines
  Nvidia/AMD/Micron/TSMC/labs/hyperscalers/contractors; entity detection sets the event
  entity so the right ticker attaches; private labs → enabler basket; AI-keyword noise
  gate). Wired into `ALL_COLLECTORS`, `config.py`, `stock_impact.py` (tickers + rules +
  default), `theme.js` (violet 🧠). Removed the overlapping AI query from `corporate_strategic.py`.
- Removed remaining **synthetic** fallbacks (`CURATED` lists) from `corporate_financial.py`,
  `operational.py`, `regulatory.py` — pipeline is now 100% live-sourced.
- **Req #1**: `LatestView.js` now renders each event's date — passes `showDate` to
  `EventCard`, and added the missing `cardDate` style in `EventCard.js`.
- **Req #2**: wrote this `TAKEOVER.md`.
- Switched `.claude/launch.json` to port **8090** (autoport-friendly; avoids 8081 prompt hang).
