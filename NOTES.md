# Build notes

Information and analysis only. Not investment advice.

## Repo

- GitHub: https://github.com/thenordicwaters/sectors_mi_teameldar
- Local folder: `sectors_api` (working title TBD)
- Stack: FastAPI (`backend/`) + SvelteKit / Svelte 5 (`frontend/`)

## Sectors v2 (do not guess paths)

Base: `https://api.sectors.app`  
Auth: `Authorization` header with the API key (not Bearer). Docs index: https://docs.sectors.app/llms.txt

Official rates from `usage-log_2026-09-20T06_54_37.126Z.csv` (67 rows, 81 credits billed). After the 21 Sept signals snapshot, **915 remaining**.

| Path | Official bill | Use |
|---|---|---|
| `GET /v2/companies/` structured | **1**/page | screener snapshot. 5 pages × 1 on 19 Sept 22:05. Also the custom `where` endpoint |
| `GET /v2/companies/` with `q=` | **3** | 17 Sept. Do not use |
| `GET /v2/foreign-flow/` | **1**/page | 23 pages × 1 on 19 Sept 22:05. Matches local ledger |
| `GET /v2/company/report/{symbol}/` | **8** full, **1** per section | 18 Sept BBCA: 8 then 1 |
| `GET /v2/subsectors/`, `/v2/industries/`, `/v2/subindustries/`, `/v2/tags/` | **1** | helper lists |
| `GET /v2/daily/{symbol}/` | **1** | per-symbol daily (do not loop the universe) |
| `GET /v2/close/` | **1**/page (docs; not in this log) | skipped — no volume |
| `GET /v2/companies/top-changes/` | **1** per classification × period (docs; not in this log) | skipped — default 10 credits |
| `GET /v2/filings/` | **1**/page, max 30 (docs; confirmed 21 Sept) | insider-buy snapshot |
| Broker `/top/` endpoints | **2** | not needed for Phase 1 |
| `GET /v2/free-float/` | **1** typical; one 200 billed **2**; **400 billed 0** | confirms structured 400 is free |
| Most other 200s in this log | **1** | helpers, index daily, idx-total, segments, corporate actions |

## Credit log

Start: 1,000. Budget: ~300 dev, ~200 snapshots, ~500 reserve.

| Date | Source | Credits | Remaining | Notes |
|---|---|---|---|---|
| 17–18 Sept | Official log, pre-snapshot exploration | 52 | 948 | Includes `q=` (3), full BBCA report (8), broker/top (2), helpers. Not in our SQLite events |
| 19 Sept 22:05 | `GET /v2/companies/` × 5 | 5 | 943 | 962 companies. Official log now shows all 5 pages |
| 19 Sept 22:05 | `GET /v2/foreign-flow/` × 23 | 23 | 920 | 668 tickers. Official matches |
| 20 Sept 13:52 | `GET /v2/subsectors/` × 1 | 1 | 919 | Official only; not our snapshot |
| 21 Sept 22:03 | `GET /v2/companies/?where=tags in ['52-w-high']` × 1 | 1 | 918 | 38 names. Structured 200 billed 1 |
| 21 Sept 22:03 | `GET /v2/filings/?transaction_type=buy&holder_type=insider` × 3 | 3 | **915** | 88 buys / 46 tickers, last 30 days, limit 30 |
| | **Running total** | **85** | **915** | Local SQLite events 32 + `SECTORS_OPENING_CREDITS_USED=53` |

Cached snapshot reruns are not in the official log (they never hit Sectors).

## Phase 2 scoring (0 credits)

Reads `company_universe` + `foreign_flow` + optional `yahoo_price_overlay`. No new Sectors calls for scoring.

**Yahoo Finance overlay (0 Sectors credits):** 12-1 momentum and 20-session average traded value from OHLCV. `scripts/enrich_yahoo.py`. Never overwrites a Sectors field.

**Documented Sectors proxies (used only if still empty):**
- Earnings yield ← `1/pe_ttm`; ROC ← `roe_ttm`
- ROA > 0 test ← `roe_ttm`
- Illiquidity ← Watchlist + Rp 100B floor; Yahoo avg traded value ≥ Rp 100M when present

**Accounting fields still missing from this snapshot:**
- Piotroski YoY, NIM, NPL, listing_date exist on the Sectors screener (`roa[2024]`, `operating_cash_flow[2024]`, `net_interest_margin[2024]`, `non_performing_loan[2024]`, `listing_date`). Richer snapshot **~5 credits**.

## Phase 2 signals

| Badge | Source | Credits |
|---|---|---|
| Mover | Cached `daily_close_change` ≥ 5% abs | 0 |
| Foreign accumulation | Cached net foreign / foreign turnover ≥ 15% and net ≥ Rp 1B | 0 |
| 52-week high | Screener `tags in ['52-w-high']` (Yahoo `high_52w` only if overlay was stored after that column existed) | **1**/page |
| Insider buying | `GET /v2/filings/?transaction_type=buy&holder_type=insider` last 30 days | **1**/page, max 30 |

Did **not** call `GET /v2/companies/top-changes/` (1 per classification×period; default **10**). Movers use the cached universe instead.

Live cache after 21 Sept snapshot: 96 movers, 38 Sectors 52-w-high tags, 36 foreign accumulation, 46 insider-buy names. `GET /api/screener` and `GET /api/stocks/{symbol}` attach these badges (0 credits).

```bash
cd backend && PYTHONPATH=. python -m app.sectors.signals_snapshot --max-credits 8
```

## Phase 2 unusual activity (0 credits)

`GET /api/unusual`. Two standard scores, each with a reason string. No new Sectors calls.

| Flag | Measured quantity | Baseline | Threshold | 22 Sept count |
|---|---|---|---|---|
| Volume spike | Latest session volume | That symbol's own trailing 60 sessions, latest excluded, min 30 sessions (Yahoo overlay) | 3.0 σ | 32 of 873 eligible |
| Foreign flow spike | Net foreign inflow ÷ 20-session average traded value | IDX cross-section that day, median and MAD × 1.4826 | 8.0 σ, net ≥ Rp 1B | 32 of 604 eligible |

Why the flow score is cross-sectional: the cache holds **one** foreign-flow day (2026-09-18). Per-symbol history would need `GET /v2/foreign-flow/{symbol}/` (1 credit × 668 tickers) or a full-universe page set per day (~23 credits/day). Neither is worth it.

Why not net ÷ foreign turnover: that ratio is bounded by ±1 and its cross-sectional MAD is ~0.34, so **3 σ is unreachable**. Measured and rejected on 22 Sept — the traded-value multiple is unbounded and works. Its cross-section is fat-tailed, so 3 σ flagged one name in nine; hence 8 σ.

Volume baselines live in `yahoo_price_overlay` (`volume_average`, `volume_standard_deviation`, `volume_baseline_sessions`). Rows stored before 22 Sept have them empty:

```bash
cd backend && PYTHONPATH=. python ../scripts/enrich_yahoo.py --force   # 921 rows, 0 Sectors credits
```

## Phase 2 custom logic (1 credit/page)

`GET /api/screener/custom?where=…` sends a **validated** structured clause to `GET /v2/companies/` — 1 credit per page, 0 on a local cache hit, one page per request (no auto-pagination). `q=` is still never used.

Field names come from the documented screener list in `backend/app/sectors/where_clause.py`. Local validation happens first, so an unknown field, an unbalanced quote, a missing `[2024]`, a stray `;`, over 400 characters or over 10 comparisons all return 422 for **0 credits**. A clause Sectors itself rejects is a structured 400, also free.

Verified 22 Sept at **0 credits** by replaying the already-cached `tags in ['52-w-high']` query through the endpoint: 38 matches, all 38 merged with their cached Score and Signals. `GET /api/screener` now rejects `filter_clause` and points here, so the billable path is always explicit.

## Phase 0 contract

Our app owns the response shapes in `backend/app/models/`. Sectors payloads are mapped in later phases; the frontend should only talk to `/api/*`.

## Phase 1 cache

SQLite file: `backend/data/sectors.db` (gitignored).

- `GET /api/screener` serves the cache with derived Score and Signal badges (0 credits unless you snapshot signals).
- `GET /api/credits` is the running counter (opening 53 + SQLite events).
- Snapshot: `python -m app.sectors.snapshot --max-credits 50`
