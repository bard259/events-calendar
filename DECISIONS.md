# DECISIONS

> Key architectural/product decisions and **why**. Append new ones at the bottom with a date.
> This is the "don't relitigate / don't reverse without reason" record.

### D1 — Pipeline is Python **stdlib-only**
No `pip install` (urllib, sqlite3, html.parser, re, math). Runs anywhere with `python3`.
Consequence: no pandas/requests/networkx/d3 — we hand-roll HTTP, parsing, and the graph layout.

### D2 — **No synthetic / curated event data**
Every event traces to a live source (`source_type` ∈ {api, scraper}). The `CURATED=[...]` fallbacks
were deleted from `corporate_financial.py`, `operational.py`, `regulatory.py`. Surface a real source or skip.
*Exception:* analytical **reference** tables (stock-impact rules, `SETUP_PROFILES`, `PREVIEWS`,
`COMPANY_TLDR`) are allowed — they're dated, sourced reference knowledge, not fabricated events.

### D3 — APIs bypass robots.txt; only HTML scrapers honor it
`HttpClient(respect_robots=False)` for APIs (SEC/openFDA/LL2/nfin) + descriptive User-Agent satisfies
ToS. Reason: stdlib `RobotFileParser` treats a 403 on robots.txt as disallow-all, which would block APIs.
429/403/Retry-After are recorded in the run report (a deliverable, not silenced).

### D4 — Forward-date mining in 3 tiers
T1 parse published calendars (Fed/BLS/BEA/EIA); T2 SEC full-text for forward earnings/PDUFA dates;
T3 Google News RSS (noisy, only emits with an extractable in-window date). `extract_dates` has the
`(?!\d)` guard so "June 2026" ≠ "June 20".

### D5 — Category 9 (AI & Compute Ecosystem) is its own lane
Dedicated `ai_industry.py` collector; entity detection sets the event's company so stock-impact attaches
the right ticker; private labs (Anthropic/OpenAI) map to a public enabler basket (NVDA/AMZN/GOOGL/MSFT).
Generic AI query removed from cat 4 to avoid cross-lane dupes.

### D6 — Stock-impact entity match is substring-based → avoid fragile short keys
Use `"arm holdings"` not `"arm"`, `"cisco systems"` not `"cisco"` (else "pharma"/"San Francisco" match).

### D7 — Company **business TL;DR**, not financial-metadata blurb
User wanted "what the company does." `company_cards.py` intro priority: curated `COMPANY_TLDR` →
**SEC SIC industry** (cached `memory/sic_cache.json`, capped per run) → `{size}-cap` fallback. Replaced
the old market-cap/estimate-count jargon. Company cards are a **separate entity** (`company_cards` table +
`company_cards.json`), linked from events via `ev.company_ticker` → `CompanyModal` ("About ›").

### D8 — Reduce technical detail on event cards
Clean titles (strip "(announced in SEC filing)", title-case ALL-CAPS), show company TL;DR instead of the
technical FTS description, minimal friendly source label (e.g. "Nasdaq" not "nfin_earnings_calendar"; no
api/scraper pill), no raw API links.

### D9 — Single-select event-type filter
Tap a category to view only it; tap again / "All" to reset (replaced multi-toggle per user request).

### D10 — Continuous learning = decision → snapshots → critic → earnings-alpha
Decision agent scores `event_previews` via learnable `memory/key_knowledge_memory.json`. Earnings-alpha
adds `pop_score` (post-earnings increase likelihood) + `lookahead_days` (pre-earnings-drift entry timing,
research-grounded: ~5–15 trading days, fades ~day 9). `evaluate_outcomes` reads `investment_price_snapshots`
for realized pre→post returns → `earnings_outcomes` → `learn` self-tunes thresholds + per-tier look-ahead
in `memory/earnings_alpha_params.json`. Learning needs snapshots on **both sides** of an event, so it
accrues over daily runs.

### D11 — Knowledge graph: force-directed, **precomputed in Python**, rendered with plain Views
Research: Fruchterman–Reingold is the standard for relationship graphs (clusters, few crossings); filter to
meaningful links, color by group. App has no graph/SVG dep, so layout is computed in `graph_build.py` and
rendered with plain RN Views (web+iOS, zero deps). Edges = companies that **co-move in the same event's
stock-impacts** (ETFs/isolates excluded). **Cluster-gravity** pulls each sector group to its own anchor so
clusters separate visually. Pan via `PanResponder`, zoom via buttons + web wheel.

### D12 — Persistence: routines commit state back to **main**
Remote daily routines run on main and commit `memory/`, `reports/`, `events.db`, and app JSON back to main
so learning persists across cloud runs (each run is a fresh checkout). `events.db` stays tracked because it
holds cross-run state (snapshots/outcomes) — accept occasional binary merge conflicts (resolve by keeping the
most complete DB; it regenerates anyway).

### D13 — Git workflow: feature branch + PR, no direct main push
Auto-mode guardrail blocks direct main pushes; use branch → PR → squash-merge. `gh` isn't installed — open/merge
PRs via the GitHub REST API using the stored git credential (read into a var, never printed).
