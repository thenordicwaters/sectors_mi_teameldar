# sectors_mi_teameldar

Finviz-style screener for IDX stocks, built for the Sectors Hackathon 2026 (Market Intelligence track).

**Information and analysis only. Not investment advice.**

## Stack

- Backend: Python FastAPI (`backend/`)
- Frontend: SvelteKit, Svelte 5, TypeScript, Tailwind (`frontend/`)
- Data: Sectors Financial API **v2** (`https://api.sectors.app/v2`)

Sectors is the core data source. Removing it would remove screening, scoring, signals, and unusual-activity flags.

## Setup

1. Copy `.env.example` to `.env` and set `SECTORS_API_KEY`.
2. Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --app-dir .
```

3. Frontend (after `npm install` in `frontend/`):

```bash
cd frontend
npm install
npm run dev
```

API contract lives in `backend/app/models/`. The screener reads a local SQLite snapshot (`backend/data/sectors.db`). Do not invent numbers.

## Snapshot (Phase 1)

Structured screener is **1 credit/page** (up to 200 rows). Full-universe foreign flow is **1 credit/page** (max 30 rows, ~20–25 pages). Cached pages cost **0**. This script never uses `q=` (3 credits).

```bash
cd backend
source .venv/bin/activate
python -m app.sectors.snapshot --dry-run
python -m app.sectors.snapshot --max-credits 50
```

Rerun against the cache any time. Use `--force` only if you accept spending credits again.

`GET /api/credits` shows the running counter. Logs print `credits=+N used=… remaining=…` after every Sectors call.

## Score

Default weights: **Quality 30, Value 25, Momentum 25, Flow 20** (overridable on `GET /api/scores`). The composite is the weighted average of available parts; missing parts are re-weighted. Fewer than three parts → unranked. Liquidity filter (market cap ≥ Rp 100B, exclude Watchlist) runs before ranking. Banks/financials are never dropped: they skip Piotroski and Magic Formula and use a financials-only quality score.

**Piotroski F-Score (Quality, 0–9 → 0–100).** Nine binary tests vs the prior fiscal year: ROA > 0, CFO > 0, ΔROA, CFO > NI, lower long-term debt ratio, higher current ratio, no new shares, higher gross margin, higher asset turnover (Piotroski 2000, *Journal of Accounting Research*). Score is the pass count. Fewer than six computable tests → no score. Not applied to financials.

**Magic Formula (Value).** Earnings yield = EBIT / enterprise value; return on capital = EBIT / (net working capital + net fixed assets). Rank both, add the ranks, convert to a 0–100 percentile (best = 100). Negative EBIT ranks worst. Excludes financials, utilities, suspended names, and names below the liquidity floors (Greenblatt 2005, *The Little Book That Beats the Market*). Cache proxy: 1/`pe_ttm` and `roe_ttm`.

**12-1 momentum.** Return from 12 months ago to 1 month ago: `(1 + r12m) / (1 + r1m) - 1`, then percentile-ranked. Under 12 months of history → no score. Filled from a Yahoo Finance OHLCV overlay when Sectors has no 1m/1y change (Sectors stays the universe). Fallback: `daily_close_change`.

**Foreign flow.** Recent net foreign buying / traded value, plus relative volume, percentile-ranked. Cache proxy: net / (foreign buy + foreign sell), relative volume = foreign turnover vs universe median.

**financials_quality.** Banks and other financials only: percentile-rank within financials on ROE, net interest margin (higher better), and NPL (lower better). NIM and NPL are not in the Phase 1 cache, so ROE carries this pillar until they are.

`GET /api/scores` and `GET /api/scores/{symbol}` read the SQLite cache only (0 Sectors credits). Yahoo prices are optional support:

```bash
cd backend && PYTHONPATH=. python ../scripts/enrich_yahoo.py
cd backend && PYTHONPATH=. python ../scripts/score_universe.py
```

## Signals

Badges on each screener row, each with a reason:

- **Mover** — `|daily_close_change| ≥ 5%` from the Sectors universe cache (0 credits). Did not call `top-changes` (that defaults to 10 credits).
- **52-week high** — Sectors screener tag `52-w-high` (1 credit/page to snapshot).
- **Foreign accumulation** — latest cached net foreign inflow ≥ Rp 1B and ≥ 15% of foreign turnover (0 credits).
- **Insider buying** — `GET /v2/filings/` buy + `holder_type=insider` in the last 30 days (1 credit/page, max 30).

```bash
cd backend && PYTHONPATH=. python -m app.sectors.signals_snapshot --max-credits 8
```

Filter the table with `GET /api/screener?signal_filter=mover`.

## Unusual activity

`GET /api/unusual` flags standard scores on the cache, each with a reason sentence. **0 Sectors credits** — nothing here calls the API.

**Volume standard score** compares the latest session with that symbol's own trailing 60 sessions, excluding the latest session so a spike cannot inflate the average it is measured against. Needs at least 30 baseline sessions and a non-zero deviation. Flagged at **3 standard deviations**. Volume history is the Yahoo OHLCV overlay.

**Foreign-flow standard score** measures net foreign inflow as a multiple of the stock's 20-session average traded value, then takes a robust standard score (median and median absolute deviation) across the IDX cross-section. Flagged at **8 standard deviations** with net flow of at least Rp 1B.

Two honest limits behind those numbers:

- The cache holds **one** Sectors foreign-flow day, so the flow score compares a stock with the market that day, not with its own history. A per-symbol history would need `GET /v2/foreign-flow/{symbol}/` per ticker, which is 1 credit each and a universe loop we do not run.
- Net flow over *foreign turnover* is trapped between −1 and 1, so it can never reach 3 standard deviations. The traded-value multiple is unbounded, which is why it is the measured quantity. That cross-section is fat-tailed rather than normal, so a 3-sigma cut flagged one name in nine; the threshold is 8.

On the 18–21 Sept snapshot this flags 32 volume spikes and 32 foreign-flow spikes across 962 companies. Screener rows carry `has_anomaly` and the flags themselves; `GET /api/screener?anomaly_only=true` keeps only flagged rows.

```text
GET /api/unusual
GET /api/unusual?anomaly_kind=volume_standard_score
GET /api/unusual?min_standard_score=10
```

Volume baselines come from the Yahoo overlay, so refresh it after a new snapshot (0 Sectors credits):

```bash
cd backend && PYTHONPATH=. python ../scripts/enrich_yahoo.py --force
```

## Custom logic (live Sectors query)

`GET /api/screener/custom` passes a validated structured `where` clause to the Sectors screener. **1 credit per page** (up to 200 rows), **0** when the same query is already in the local HTTP cache. Natural-language `q=` (3 credits) is never used.

Validation runs locally first, so a clause we can reject ourselves costs nothing: every field name is checked against the documented screener list, yearly fields must use `revenue[2024]` and quarterly fields `revenue_q[Q1-2024]`, quotes and brackets must balance, and the clause is capped at 400 characters and 10 comparisons. A rejected clause returns 422 with a suggestion; a clause Sectors itself rejects returns 422 and is free (a structured 400 is not billed).

Matches that exist in the snapshot come back with their Score, Signal badges and Anomaly flags attached. Matches outside the snapshot come back with an empty score rather than a guess.

```text
GET /api/screener/custom/fields                                    # what the box accepts, 0 credits
GET /api/screener/custom?where=market_cap > 10000000000000&dry_run=true   # planned cost, 0 credits
GET /api/screener/custom?where=sector = 'Financials' and roe_ttm > 0.15
GET /api/screener/custom?where=tags in ['52-w-high'] and yield_ttm > 0.03
```

`GET /api/screener` stays on the cached snapshot and rejects a `filter_clause`, so the billable path is always the explicit one.

