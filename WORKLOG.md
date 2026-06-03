# WORKLOG

> Chronological record of substantial work, newest at top. Append an entry per session/change set
> so the chat history isn't needed. See `DECISIONS.md` for the "why", `ROADMAP.md` for "next".

## 2026-06-03 — Yahoo earnings attempt + Nvidia/SpaceX/Anthropic connection rankings
- **Task 1 (earnings dates Jun–Dec)**: Yahoo Finance calendar is a JS/consent shell; its data API
  (`query2…/v1/finance/visualization`, crumb+cookie) **hard-blocks datacenter IPs (HTTP 429/406)**.
  Wrote `pipeline/scrape_yahoo_earnings.py` (real crumb+viz scraper, dedups by ticker+date, records
  the ToS/429 block, integrates as cat-3 `yahoo_earnings_calendar` events) — runnable from an
  unblocked env. The reachable equivalent (Nasdaq via nfin) already holds **Jun–Jul = 1,023** real
  earnings; the Aug–Dec bulk pull **also 429-rate-limited** (Retry-After) so it added 0 — the daily
  routine fills more day-by-day within limits. Earnings remain integrated in DB + calendar app.
- **Task 2 (connection measurement + rankings)**: `pipeline/connection_rank.py` — builds one weighted
  undirected relationship graph from the curated ecosystem map (`anthropic_graph.json`, incl. private
  hubs SpaceX/Anthropic) + DB `stock_graph_edges`, weights edges by relationship TYPE, and runs a
  **truncated weighted diffusion (3 hops, 0.5/hop)** from each hub to score every company's connection
  strength. Ranks public companies per hub, annotates each with its next earnings date + strongest link.
  Outputs `app/assets/connection_rankings.json` + `pipeline/reports/research/connection_rankings_<date>.md`.
  Top: **Nvidia** → TSM/MSFT/AMZN/MRVL/GOOGL…; **SpaceX** → MSFT/NVDA/STM…; **Anthropic** →
  NVDA/MSFT/AMZN/GOOGL/AVGO/CRM/CEG…

## 2026-06-03 — Expandable event cards + Robinhood-style stock panel
- Replaced the detail-heavy `EventCard` layout with a collapsed/expanded card. Collapsed state now
  shows only event type, importance, title, entity/date, and industry chips; tapping expands in place.
- Added `app/src/StockCard.js`: expanded state shows a stock card with ticker/name, company mission or
  business summary, latest price anchor, green/red trend line, and range buttons **1D / 1W / 1M / 3M / 1Y**
  styled after Robinhood's compact chart flow.
- Added `pipeline/export_stock_prices.py` and `app/assets/stock_prices.json`. The exporter anchors
  charts to any stored quote snapshot, then fills compact deterministic series until a real historical
  price feed is added. `run_daily_agents.py` now refreshes the stock trend asset after snapshots/export.
- Verification: Python + JS syntax checks passed; `npx expo export --platform web --output-dir
  /tmp/events-expandable-stock-card-web` passed; browser check expanded a Latest event card and confirmed
  the stock card and range switch (`1M` → `3M`) update.

## 2026-06-03 — Industry labels on stock cards + event filtering
- Added `pipeline/industry_labels.py`: a coarse, user-facing industry labeler that maps ticker/name/SIC
  context into stable app labels such as **AI & Cloud Software**, **Semiconductors**,
  **Communications**, **Financials**, **Healthcare**, **Energy & Utilities**, and
  **Aerospace & Space**.
- Added `company_cards.industry_label` with a lightweight migration in `db.init_db()`, rebuilt
  `app/assets/company_cards.json`, and exported event-level `industry_label` / `industry_labels`
  in `app/assets/events.json` from the primary company and impacted tickers.
- Added an **Industry** chip row in the app calendar views. It single-selects industry labels and
  combines with the existing Event type chips; event cards and company modals now display the label.
- Verification: `python3 -m py_compile pipeline/industry_labels.py pipeline/company_cards.py
  pipeline/export_for_app.py pipeline/db.py`; JS `node --check`; rebuilt company cards/events;
  `npx expo export --platform web --output-dir /tmp/events-industry-filter-web`; browser check
  confirmed the industry row renders and **AI & Cloud Software** filters from **1,198 → 40** events.

## 2026-06-03 — DB-backed public-company stock graph + selected-stock view
- Added `pipeline/stock_graph.py`: builds a DB-backed stock knowledge graph from the SEC
  `company_tickers_exchange.json` listed-company universe, enriched with local `company_cards`,
  `event_stock_impacts`, event primary-company links, same-SEC-industry peers, and public-company
  edges from the Anthropic ecosystem reference graph.
- Added SQLite tables `stock_graph_nodes` and `stock_graph_edges`; current build wrote **7,568**
  exchange-listed company nodes and **472** evidence-backed relationships. Export:
  `app/assets/stock_graph.json`.
- Added `app/src/StockGraphView.js` and wired it into `GraphView` as a third mode:
  **Ecosystem map / Co-movement / Stock graph**. The Stock graph page has ticker/company search,
  Direct vs 2-hop depth, relationship-type filters, pan/zoom, local graph rendering, and relationship
  details for the selected ticker.
- Wired `stock_graph.build(refresh_sec=False)` into `run_daily_agents.py` so daily graph refreshes
  reuse the local SEC exchange cache; run `python3 pipeline/stock_graph.py` manually to refresh the
  SEC-listed ticker universe from the network.
- Verification: `python3 pipeline/stock_graph.py` fetched SEC exchange data, populated DB/export;
  `python3 -m py_compile pipeline/stock_graph.py pipeline/db.py pipeline/run_daily_agents.py` passed;
  `npx expo export --platform web --output-dir /tmp/events-stock-graph-web` passed; browser QA checked
  Graph → Stock graph, NVDA default view, AAPL search/selection, and 390px mobile layout.
- Extended `stock_graph.py` with continuously-refreshable focus snapshots:
  `--center TICKER` builds a selected-company 1/2-hop subgraph; `--theme ai-space-earnings`
  selects AI/Space-related companies with earnings in the next 92 days, writes
  `stock_graph_focus_runs`, and exports `app/assets/stock_focus_graphs.json`.
- Executed the AI/Space earnings focus once for **2026-06-03 → 2026-09-03**:
  **37 center tickers**, **65 nodes**, **115 edges**. Latest focus run id: 2.
- Created active Codex automation **daily-ai-space-stock-graph-refresh** to run the AI/Space
  earnings focus refresh daily at 07:15 local time.
- Added reusable SEC filing relationship scanning to `stock_graph.py`: `--sec-mentions TICKER`
  fetches recent 10-K/10-Q filings, matches public-company names/brands, classifies the context into
  existing relationship types (`supplies`, `customer`, `partners`, `contracts`, `invests_in`, `powers`)
  with `sec_mention` only as an ambiguous fallback, then exports the selected-stock focus graph.
  Selected tickers persist in `pipeline/memory/stock_graph_sec_mentions.json`; the last successful
  SEC-derived edges are cached in `pipeline/memory/stock_graph_sec_edges.json` so later offline/network-
  failed graph rebuilds do not blank the selected-stock links.
  Executed `--sec-mentions IOT --center IOT`: IOT now links to **AMZN** (`supplies`, AWS hosting) and
  **VZ** (`customer`, Verizon Connect market/customer context). Current full stock graph: **7,568**
  nodes / **474** edges; IOT focus graph: **3** nodes / **2** edges.

## 2026-06-03 — Anthropic map readability pass
- Redesigned `app/src/GraphView.js` ecosystem mode around a **focus + context** flow:
  default view now shows **Direct** Anthropic relationships only (11 entities / 19 typed links),
  with **Near** (2-hop) and **Full** expansion filters.
- Added relationship-type narrowing chips. When all types are active, tapping a type now isolates
  that link class (e.g. **Supply** → 5 entities / 5 direct supply links); **All** restores the full set.
- Replaced the dense force-layout display in ecosystem mode with a radial focus layout grouped by
  sector and distance from Anthropic; same-sector nodes get extra spread to reduce label collisions.
- Added selected-node relationship details below the plot, with typed edge notes and a public-company
  **Card** action. Direct-view nodes were enlarged and the plot height tightened for desktop/mobile.
- Verification: `npx expo export --platform web --output-dir /tmp/events-expo-web` passed; browser QA
  checked Direct, Near, Supply-only, and 390px mobile viewport.

## 2026-06-03 — Anthropic ecosystem knowledge graph (branch `company-knowledge-graph`, PR #4)
- New **`pipeline/knowledge_graph.py`**: curated, typed, directed relationship graph centered on
  Anthropic — investors (Amazon ~$33B, Google ~$40B, Microsoft $5B, Nvidia $10B, Menlo/Lightspeed/
  ICONIQ/Salesforce), compute suppliers (AWS Trainium / Google TPU / Azure; Broadcom & Marvell
  co-design), chip chain (TSMC fab; SK Hynix/Micron/Samsung HBM; ASML/AMAT/Lam/KLA equip), energy/
  nuclear (Constellation/Talen/Oklo/Kairos/X-energy/Vistra/Cameco power the data centers), and space
  (SpaceX/Starlink ← STMicro/Wistron/Filtronic; → NASA/Space Force). 51 nodes / 80 typed edges
  (invests_in/supplies/powers/partners/customer/contracts). Cluster-separated FR layout, Anthropic
  pinned center → `app/assets/anthropic_graph.json`. Research-grounded (web).
- **GraphView** generalized: toggle **Ecosystem map** ⟷ **Co-movement**; ecosystem edges colored by
  relationship type with a relationship legend; nodes tap → company card when public.

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
