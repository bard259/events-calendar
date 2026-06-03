# WORKLOG

> Chronological record of substantial work, newest at top. Append an entry per session/change set
> so the chat history isn't needed. See `DECISIONS.md` for the "why", `ROADMAP.md` for "next".

## 2026-06-03 — Knowledge graph v2 + persistent docs (branch `company-knowledge-graph`, PR #4)
- **Company relationship knowledge graph**: `pipeline/graph_build.py` builds nodes (companies) +
  edges (co-move in same event's stock-impacts), Fruchterman–Reingold layout in stdlib Python →
  `app/assets/company_graph.json`. New **Graph** tab (`app/src/GraphView.js`).
- **v2**: cluster-separated layout (cluster-gravity per sector group + softened cross-cluster repulsion)
  with cluster labels; **pan** (PanResponder) + **zoom** (+/−/reset buttons, mouse-wheel on web).
  Nodes tap → CompanyModal. First build: 21 nodes / 16 edges.
- Wired `graph_build.build()` into `run_daily_agents.py` (daily refresh).
- Created **ROADMAP.md / DECISIONS.md / WORKLOG.md**; CLAUDE.md points to the doc set.

## 2026-06-03 — Merged PR #3 (AVGO recap) ; integration to main
- Merged **PR #2** (integrated decision/critic + company cards + earnings-alpha) → main (squash 2366a14),
  resolving an `events.db` binary conflict (kept integrated DB).
- Merged **PR #3** (AVGO pre-print recap, a2963f3): the scheduled pre-print routine **caught a baseline
  error** — Q1 FY26 AI revenue was $8.4B (not $4.1B); Q2 guide $10.7B/+140%. Resolved the
  `earnings_preview.py` conflict by keeping corrected content + the app's decision/confidence/significance.
- **Scheduled-run status** at the time: `Daily Events Collector` fired (0 new events, committed 64fd424);
  AVGO pre-print fired → PR #3; `Daily earnings agents` first run pending (22:00 UTC).

## 2026-06-02 — Company cards (#2) + continuous-learning earnings-alpha (#3) + scheduling
- **Company cards** (`company_cards.py`, `company_cards` table, `company_cards.json`): per-ticker business
  intro (curated TL;DR > SEC SIC industry (cached/capped) > size fallback). App: `CompanyModal` + "About ›".
  Events carry `company_ticker`. Replaced jargon intro in `export_for_app.py`. 1039 cards (29 curated /
  244 SEC / 766 size).
- **Earnings-alpha** (`analysis/earnings_alpha.py`, tables `earnings_alpha`/`earnings_outcomes`): pop-score +
  look-ahead days merged into `ev.preview`; outcome eval from price snapshots; self-tuning params in
  `memory/earnings_alpha_params.json`. Shown in EVENT CALL block.
- **Single-select** event-type filter; **reduced technical detail** on event cards.
- **Integrated** Codex's decision/critic subsystem (scrape_earnings_previews, decision_agents,
  run_daily_agents, export_agent_reports, Reports tab, memory/, reports/).
- **Scheduled** remote routine `Daily earnings agents (decision+critic+learning)` (22:00 UTC, commits memory
  to main) + 3 one-time AVGO recap routines (Jun 3/4).
- Docs synced: CLAUDE.md, memory `events-project.md`, MEMORY.md.

## 2026-06-02 (earlier) — AI category 9, setup-signals, earnings-preview, Latest dates (PR #1)
- **Category 9 — AI & Compute Ecosystem** collector (`collectors/ai_industry.py`) + AI stock-impact rules +
  violet 🧠 theme. Removed remaining synthetic fallbacks (100% live-sourced).
- **Setup-signals** (`analysis/setup_signals.py`, `event_setups`): VSCO/VSXY-style asymmetry score (short
  interest + activist + analyst-trend + catalyst) → ⚡ SETUP badge.
- **Earnings-preview** (`analysis/earnings_preview.py`, `event_previews`): consensus bar / implied move /
  lean / bull-bear-watch → 📊 day-detail block. Seeded AVGO + comparables (VSXY/CTRN/CAL/CRON/PLUS/GEF).
- Ticker fix **VSCO→VSXY**. **Latest** view shows each event's date.
- Research: Victoria's Secret +~50% on 6/2 (short squeeze + activist + turnaround); Broadcom 6/3 preview.
- Wrote `TAKEOVER.md`. PR #1 merged (01dc401).

## Pre-2026-06-02 — Foundation (initial commit 88da3f9)
- Jun–Dec 2026 event pipeline (9 categories, 3-tier mining), SQLite, stock-impact engine,
  Expo app (Month/Week/Day/Latest), storage estimate + rate-limit/ToS reporting.
