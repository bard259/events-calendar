# ROADMAP

> Living snapshot of **current state + what's next**. Pair with `DECISIONS.md` (why) and
> `WORKLOG.md` (what happened). `CLAUDE.md` has conventions; `TAKEOVER.md` is the cold-start guide.

_Last updated: 2026-06-03_

## Current state (snapshot)
- **Pipeline** (Python stdlib): 9 event categories, Jun–Dec 2026, SQLite (`pipeline/events.db`),
  **100% live-sourced** (api/scraper, no synthetic). ~1,200 events (the nfin/Nasdaq earnings
  calendar dominates at ~1,023).
- **Enrichment layers**: stock-impact rules → `event_stock_impacts`; setup-signals → `event_setups`
  (⚡ badge); earnings-preview → `event_previews` (📊 EVENT CALL); earnings-alpha → `earnings_alpha`
  (pop-score + look-ahead days); company cards → `company_cards`; knowledge graph → `company_graph.json`.
- **Agents** (`run_daily_agents.py`): decision → price snapshots → critic → earnings-alpha learning.
  Learnable memory in `pipeline/memory/*.json`. Reports in `pipeline/reports/`, app **Reports** tab.
- **App** (Expo, web+iOS): Month/Week/Day/Latest/**Graph**/Reports; single-select event-type filter;
  event cards with company TL;DR + ⚡ setup + 📊 EVENT CALL; **CompanyModal** (About ›); **Graph** tab
  (cluster-separated, pan/zoom).
- **Automation** (remote routines on `bard259/events-calendar`):
  - `Daily Events Collector` (14:00 UTC) — `daily_update.py`, commits to main.
  - `Daily earnings agents (decision+critic+learning)` (22:00 UTC) — `run_daily_agents.py`, commits memory to main.
  - 2 remaining one-time AVGO recap runs (Jun 4 15:00 & 20:30 UTC).

## Open items / next steps
- [ ] **Merge PR #4** (`company-knowledge-graph`: Graph tab + clustered/zoomable layout + these docs).
- [ ] **Daily routine commit-list**: add `app/assets/company_graph.json` (and confirm `company_cards.json`)
      to the `Daily earnings agents` routine so the daily-refreshed graph/cards persist to the repo.
      (Update via the `schedule` skill / RemoteTrigger; needs full job_config resend.)
- [ ] **Graph enrichment**: graph is sparse (~21 nodes) because most events are single-company
      earnings (link only to sector ETFs). Grows as multi-company AI/defense/energy events accumulate.
      Consider adding explicit relationship edges (supplier/customer, AI-ecosystem roster) beyond co-impact.
- [ ] **Company-card SEC coverage** fills incrementally (250/run, cached in `memory/sic_cache.json`);
      ~244/1039 have real SEC industries so far — let it accrue or raise `--sec-cap`.
- [ ] **Earnings-alpha learning** needs accumulated pre+post price snapshots to actually self-tune
      (`earnings_outcomes` empty until earnings pass with snapshots both sides). Verify after a few daily runs.
- [ ] **`events.db` merge conflicts** recur because it's a tracked binary touched by parallel routines.
      Decide: keep committing it (needed for cross-run learning state) vs. a cleaner persistence path.
- [ ] **Preview coverage**: `event_previews` now spans the whole earnings calendar (generic payloads);
      curated `earnings_preview.PREVIEWS` overrides marquee names. Keep refreshing dated snapshots.

## Known risks / watch-outs
- Two engines historically overlapped on `event_previews` (my curated `earnings_preview` vs Codex's
  scrape) — now integrated (scrape calls `earnings_preview.enrich_and_save`). Don't reintroduce a competing writer.
- Remote routines run on **main** and commit back to main; keep main green or they no-op/guard.
- All "analysis" tables (`SETUP_PROFILES`, `PREVIEWS`, `COMPANY_TLDR`) are **dated sourced snapshots** —
  refresh discipline matters; they are reference data, not events.
