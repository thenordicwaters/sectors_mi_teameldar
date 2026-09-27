# Phase 2, explained (beginner guide)

Information and analysis only. Not investment advice.

This file is a study note for **what we built in Phase 2** and **why the code looks the way it does**. You do not need to memorize it. Read a section, then open the file it points to.

Phase 2 is the “derived insight” part of the hackathon. A table of raw Sectors numbers is not enough. We had to **compute** something: a Score, and Signal badges.

---

## 1. The one-picture version

Think of three layers, like a kitchen:

1. **Pantry (Phase 1 cache).** We already downloaded IDX companies and foreign flow from Sectors into a local SQLite file: `backend/data/sectors.db`. Opening the pantry is free. Calling Sectors again costs **credits**.
2. **Recipes (Phase 2 math).** Scoring methods and signal rules. They only look at numbers we already have (plus optional Yahoo prices). They do not call Sectors.
3. **Plate (API).** FastAPI serves `/api/screener`, `/api/stocks/{symbol}`, `/api/scores`. The frontend will later show this as a Finviz-style table.

```text
Sectors API  --credits-->  SQLite cache  --0 credits-->  Score + Signals  -->  /api/screener
                              ^
                              optional Yahoo OHLCV (0 Sectors credits)
```

**Rule we never break:** do not invent numbers. If a field is missing, the score part is `null` and the badge is simply not shown.

---

## 2. Words you will see in the code

| Word | Meaning in this repo |
|---|---|
| **IDX** | Indonesia Stock Exchange. Tickers look like `BBCA.JK` (4 letters + `.JK`). |
| **Sectors** | The paid API. Core data source. Removing it would remove the product. |
| **Credit** | One unit of Sectors billing. We have a 1,000 budget. Structured screener = 1 per page. |
| **Snapshot** | A script that copies Sectors pages into SQLite so we can reuse them for free. |
| **Cache hit** | Same HTTP request already stored. Cost = **0**. |
| **SQLite** | A single-file database. Ours lives at `backend/data/sectors.db` (gitignored). |
| **Derived** | Something we computed, not copied from Sectors. Score and badges are derived. |
| **Proxy** | A stand-in when the real formula field is not in the cache. We label it in `adapter_notes`. |
| **Percentile rank** | “Where does this stock sit vs peers, 0–100?” 100 = best in the group. |
| **Composite** | The final 0–100 score made from Quality + Value + Momentum + Flow. |
| **Badge / signal** | A small flag such as “Mover” or “Insider buying”, always with a **reason** string. |
| **Standard score** | The z-score: how many standard deviations a value sits from its baseline. |
| **Robust** | Built on median and median absolute deviation instead of mean and σ, so one huge outlier cannot hide itself. |
| **Cross-sectional** | Compared with other stocks on the same day, rather than with this stock's own history. |
| **Isolation** | Scoring *methods* must not import HTTP, FastAPI, or SQLite. Pure math only. |

---

## 3. What was already there (Phase 1) vs what Phase 2 added

**Phase 1 (done earlier):** talk to Sectors safely, count credits, snapshot the company universe and one day of foreign flow.

**Phase 2 added four products:**

1. **Score** — a 0–100 ranking with a breakdown (quality / value / momentum / flow).
2. **Signals** — badges: movers, 52-week high, foreign accumulation, insider buying.
3. **Unusual activity** — standard scores (z-scores) on volume and foreign flow, with a reason per flag.
4. **Custom logic** — your own validated Sectors `where` query, the only part of the app that spends credits at request time.

Still **not** done (later phases): the Svelte UI.

---

## 4. How a screener row is built (the important path)

When someone hits `GET /api/screener`, this happens. No Sectors call.

1. `backend/app/routers/screener.py` receives the request (`sort_by`, `signal_filter`, page).
2. `backend/app/sectors/repository.py` loads every company from SQLite **once**, then keeps the result in memory until the database changes.
3. For each company it asks:
   - `ScoringService` → `ScoreBreakdown` (or `null` parts if unranked)
   - `badges_for_stock` → list of `SignalBadge`
   - `detect_unusual_activity` → list of `AnomalyFlag` (once for the whole universe, because one of the two scores is cross-sectional)
4. It sorts, optionally keeps only rows with a given badge or a flag, then returns one page (default 20 rows).

`GET /api/stocks/BBCA` reuses the same cached rows. Still 0 credits.

If you want to watch this in the debugger, put a breakpoint in `_build_derived_rows` in `repository.py`. That function is the glue.

---

## 5. Scoring, slowly

### 5.1 Folder map

Everything lives under `backend/app/services/scoring/`.

```text
scoring/
  types.py          Shared shapes: StockInputs, MethodResult, Weights
  config.py         Weights, liquidity floors, “what is a bank?”
  stats.py          percentile_rank helper
  base.py           Common MethodResult constructor
  registry.py       List of methods to run
  service.py        Public entry: universe in, ranked results out
  adapters/
    sectors.py      SQLite / Sectors / Yahoo  -->  StockInputs
  methods/          Pure formulas (no HTTP, no SQLite)
    piotroski.py
    magic_formula.py
    momentum.py
    foreign_flow.py
    financials_quality.py
    composite.py    Mixes the four pillars into one number
```

**Why isolation?** So a formula cannot accidentally spend credits, and so we can unit-test math with fake stocks. The test `backend/tests/test_scoring_isolation.py` fails if a method file imports `httpx`, `fastapi`, or `sqlite3`.

### 5.2 The adapter (the translator)

Sectors field names (`pe_ttm`, `roe_ttm`, `foreign_buy_idr`) are **not** what methods use.

`adapters/sectors.py` maps cache columns → a neutral object called `StockInputs` (`price_to_earnings`, `return_on_equity`, …).

Methods are written as if the data could come from anywhere. Only the adapter knows Sectors.

That file also applies **proxies** when the textbook field is missing, and writes a human note, for example:

- earnings yield ≈ `1 / pe_ttm` (real Magic Formula wants EBIT / enterprise value)
- return on capital ≈ `roe_ttm`
- ROA test ≈ `roe_ttm` until we snapshot real `roa`

A proxy is worse than the real field, but it is honest: the note stays on the result.

### 5.3 The four pillars (weights)

Default weights in `config.py`:

| Pillar | Weight | Method | Who it applies to |
|---|---|---|---|
| Quality | 30 | Piotroski F-Score | Non-financials |
| Quality | 30 | `financials_quality` | Banks / Financials sector |
| Value | 25 | Magic Formula | Non-financials, non-utilities, liquid names |
| Momentum | 25 | 12-1 return | Anyone with enough price history |
| Flow | 20 | Foreign flow | Anyone with a cached flow row |

Banks are **never dropped** from the universe. They skip Piotroski and Magic Formula (those formulas break on bank balance sheets) and get `financials_quality` instead.

### 5.4 Each method in plain language

**Piotroski (`methods/piotroski.py`)**  
Nine yes/no accounting tests vs last year (ROA positive, cash flow positive, debt down, …). Score is how many passed, 0–9, later scaled to 0–100. If fewer than **6** tests can be computed, we return no quality score rather than a fake 2/9. Our Phase 1 cache does **not** have most of these year-over-year fields, so Quality is often `null` today. That is expected.

**Magic Formula (`methods/magic_formula.py`)**  
Rank cheap (high earnings yield) and rank good businesses (high return on capital). Add the two ranks. Convert to a 0–100 percentile (best = 100). Negative earnings rank worst. We currently use PE and ROE proxies.

**Momentum (`methods/momentum.py`)**  
Classic **12-1**: return from 12 months ago to 1 month ago, so the latest month does not dominate.

```text
12-1 = (1 + return_12m) / (1 + return_1m) - 1
```

Sectors did not give us 1-month / 12-month returns in the Phase 1 snapshot. We fill those from **Yahoo Finance** OHLCV (`backend/app/enrichment/yahoo.py`). Sectors still decides *which stocks exist*. Yahoo only fills empty price fields. If Yahoo is missing too, we fall back to one-day `daily_close_change` and say so in the notes.

**Foreign flow (`methods/foreign_flow.py`)**  
Net foreign buying relative to foreign turnover, plus how large that turnover is vs the universe median. Cache has one trading day, not a 20-day window, so this is a **same-day proxy**.

**financials_quality (`methods/financials_quality.py`)**  
Among financials only, percentile-rank ROE (and NIM / NPL when we have them). NIM and NPL are not in the Phase 1 cache, so ROE carries this pillar for now.

**Composite (`methods/composite.py`)**  
1. Drop illiquid names from *ranking* (Watchlist board, or market cap under Rp 100B). They still appear on the screener with `overall_score = null`.
2. Count how many of the four pillars exist.
3. Need **at least 3** pillars or the stock is unranked.
4. Re-weight the weights over the pillars that exist. Example: Quality missing, others present → Value/Momentum/Flow share 100% in their original proportions.
5. Rank everyone who has a score. Rank 1 = highest composite.

Then `ScoringService` sorts results by rank.

### 5.5 Why so many scores are null

On the live cache (962 companies) about **510** get a numeric overall score. The rest fail a gate: too small, Watchlist, or fewer than three pillars.

That is a feature. A number with no data behind it would be fake.

### 5.6 Try scoring yourself (0 credits)

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python ../scripts/score_universe.py
```

API (backend must be running):

```text
GET /api/scores
GET /api/scores/BBCA
GET /api/scores?quality=40&value=20&momentum=20&flow=20
```

---

## 6. Signal badges, slowly

A badge is **not** a score. It is a yes/no flag plus a sentence you could read on a video.

Code: `backend/app/services/signals.py`  
Snapshot (the two that cost credits): `backend/app/sectors/signals_snapshot.py`

### 6.1 The four badges

| Badge | Rule | Data | Credits to refresh |
|---|---|---|---|
| **Mover** | Absolute daily change ≥ **5%** | Cached `daily_close_change` | 0 |
| **52-week high** | Sectors tag `52-w-high` | Extra screener snapshot | **1 / page** |
| **Foreign accumulation** | Net inflow ≥ **Rp 1B** and ≥ **15%** of (buy+sell) | Cached foreign flow | 0 |
| **Insider buying** | Latest insider **buy** filing in last 30 days | `/v2/filings/` | **1 / page**, max 30 rows per page |

We **did not** call `/v2/companies/top-changes/`. Docs price that at 1 credit per classification × period, and the default combo is **10 credits**. Movers from the universe cache are cheaper and good enough.

Live snapshot on 21 Sept (4 credits, 915 remaining):

- 96 movers
- 38 names with Sectors `52-w-high`
- 36 foreign accumulation
- 46 names with an insider buy (88 filings, we keep the latest per ticker)

### 6.2 52-week high, two sources

Preferred: Sectors screener filter `tags in ['52-w-high']` (documented field, not guessed).

Backup: Yahoo 52-week high, if close is within 2% of that high. The existing Yahoo overlay rows were saved **before** we added the `high_52w` column, so that backup is empty until you re-run Yahoo with `--force`. The Sectors tag is the real badge today.

### 6.3 Why each badge has a `reason`

Hackathon rule: derived insight must be explainable. Example reason:

```text
Jane Doe bought 1,000 shares (Sectors filings, 2026-09-18).
```

The UI can show the badge; the video can read the reason.

### 6.4 Refresh signals

Dry run first (prints planned cost, no HTTP):

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python -m app.sectors.signals_snapshot --dry-run
PYTHONPATH=. python -m app.sectors.signals_snapshot --max-credits 8
```

Cached reruns cost **0**. `--force` hits Sectors again and spends credits.

Filter from the API:

```text
GET /api/screener?signal_filter=mover
GET /api/screener?signal_filter=fifty_two_week_high
GET /api/screener?signal_filter=foreign_accumulation
GET /api/screener?signal_filter=insider_buying
```

---

## 7. Unusual activity, slowly

A **standard score** (the usual name is z-score) answers one question: *how far from normal is this number, counted in normal-sized steps?*

```text
z = (value - average) / standard deviation
```

- `z = 0` → exactly average
- `z = 3` → three standard deviations away. On a bell curve that is roughly a 1-in-700 day.

Code: `backend/app/services/anomalies.py`. Route: `GET /api/unusual`. Cost: **0 credits**. Every flag carries a `reason` sentence, same rule as the badges.

### 7.1 Volume: a stock against its own past

This is the textbook version, because we *do* have history: Yahoo gives us a year of daily volume for free.

| Piece | Choice | Why |
|---|---|---|
| Baseline | Trailing **60 sessions** | About three months of trading habits |
| Latest session | **Excluded** from the baseline | Otherwise the spike inflates the average it is measured against |
| Minimum | **30** baseline sessions, deviation above 0 | A new listing has no "normal" yet |
| Threshold | **3.0** | 32 of 873 eligible tickers on the 21 Sept overlay |

The three numbers per symbol (`volume_average`, `volume_standard_deviation`, `volume_baseline_sessions`) are stored in `yahoo_price_overlay` when you run the Yahoo script, so the API only divides.

```text
Volume 3.8M shares is 24.6 standard deviations above its 60-session average of
157.1k shares, about 24.2x normal (Yahoo OHLCV overlay, 2026-09-21).
```

### 7.2 Foreign flow: a stock against the market that day

Here we have a problem. The cache holds **one** Sectors foreign-flow day. You cannot compute "unusual for this stock" from a single observation. Buying history would cost 1 credit per ticker (668 of them) or ~23 credits per extra day for the whole universe.

So this score is **cross-sectional**: it compares one stock with every other stock on that same day. The reason string says so, because that is a weaker claim than the volume one.

**What we measure**, after a false start worth remembering:

| Attempt | Quantity | Result |
|---|---|---|
| First | net foreign inflow ÷ **foreign turnover** | Dead end. The ratio cannot leave −1…1, and the cross-section's spread is already 0.34, so 3 standard deviations is mathematically impossible. Zero flags, every day. |
| Second | net foreign inflow ÷ **20-session average traded value** | Works. Unbounded, and it reads as "foreign investors alone moved 7x what this stock trades on a normal day". |

**Robust**, not plain, statistics: we use the **median** and the **median absolute deviation** (MAD × 1.4826 estimates a standard deviation) instead of mean and σ. With a plain mean, one Rp 40B outlier drags the average toward itself and hides the very thing we are hunting. That is called masking.

```text
Foreign investors were net sellers of Rp 40.2B on 2026-09-18, 7.2x this stock's
20-session average traded value: 109.2 robust standard deviations below the IDX
median across 604 tickers that day (Sectors foreign flow over Yahoo traded value,
cross-sectional).
```

### 7.3 Why the two thresholds differ (3 vs 8)

A bell curve is the assumption behind "3 sigma is rare". The IDX flow cross-section is not a bell curve; it is **fat-tailed**. At 3.0 it flagged one name in nine, which is not unusual by any normal use of the word. At 8.0 the list is about 30 names whose foreign flow was several normal days of trading in one session.

Both numbers are named constants at the top of `anomalies.py`, next to the sentence explaining them. Change them there and re-run the tests.

### 7.4 Where the flags show up

| Place | What you get |
|---|---|
| `GET /api/unusual` | The flags themselves, biggest absolute score first, plus `method_notes` |
| `GET /api/screener` | `has_anomaly` and the `anomalies` list on each row (the Anomaly column) |
| `GET /api/screener?anomaly_only=true` | Only flagged rows |
| `GET /api/stocks/BBCA` | The same flags for one stock |

```text
GET /api/unusual?anomaly_kind=volume_standard_score
GET /api/unusual?min_standard_score=10
```

`min_standard_score` only tightens: detection has already stopped at the floor, so asking for less than 3 is a 422 rather than a lie.

### 7.5 Refresh

Volume baselines are Yahoo-derived, so after a new snapshot:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python ../scripts/enrich_yahoo.py --force   # 921 rows, 0 Sectors credits
```

Rows saved before 22 Sept have no baseline columns, so they simply produce no volume flag until you do this.

---

## 8. Custom logic: the user's own Sectors query

Finviz gives you fixed dropdowns. We also allow a real query, which is one of the "screeners with custom logic" the track asks for.

`GET /api/screener/custom?where=…` is the **only** route that spends credits when someone browses: **1 credit per page** (up to 200 rows), **0** if that exact query is already in `http_cache`. One page per request, so a click can never trigger 23 pages.

### 8.1 Validate first, spend second

`backend/app/sectors/where_clause.py` holds the documented field list and checks the clause locally *before* any HTTP call. Two reasons: a rejected clause should cost nothing, and "market_capp is not a Sectors screener field, did you mean market_cap?" is a better answer than a 400.

| Check | Example that fails |
|---|---|
| Known field name | `market_capp > 1000` (suggests `market_cap`) |
| Yearly fields need a year | `revenue > 1000` → `revenue[2024] > 1000` |
| Quarterly fields need a quarter | `revenue_q[2024]` → `revenue_q[Q1-2024]` |
| No bracket on plain fields | `market_cap[2024]` |
| Balanced quotes and brackets | `sector = 'Financials` |
| Nothing but the documented characters | `market_cap > 1000; drop table …` |
| Size limits | over 400 characters, or over 10 comparisons |

String literals are cut out before those checks, so `company_name like '%energi%'` is fine and a `;` hiding inside quotes cannot sneak through as syntax.

### 8.2 What comes back

Matches that are in the snapshot arrive with their **Score, Signal badges and Anomaly flags** attached. Matches outside the snapshot arrive with an empty score and a note saying so — we do not guess a score from a single live row.

```text
GET /api/screener/custom/fields                          # what the box accepts, 0 credits
GET /api/screener/custom?where=market_cap > 10000000000000&dry_run=true
GET /api/screener/custom?where=sector = 'Financials' and roe_ttm > 0.15
```

`dry_run=true` validates and prints the planned cost without calling Sectors. Use it while building the UI.

`GET /api/screener` now **rejects** a `filter_clause` and points here, so nobody spends a credit by accident on what looks like a cached endpoint.

### 8.3 How it was verified for free

The 21 Sept signals snapshot already paid for `tags in ['52-w-high']`. Replaying exactly that query (same `where`, `order_by`, `limit`, `offset`) through the new endpoint was a cache hit: 38 matches, all 38 carrying their cached Score and Signals, **0 credits**, counter still at 915.

---

## 9. Extra data: Yahoo overlay

File: `backend/app/enrichment/yahoo.py`  
Script: `scripts/enrich_yahoo.py`

Yahoo is **supporting**, not a second universe. It never overwrites a Sectors value. It only fills empty `return_1m`, `return_12m`, volume, average traded value, and (on new downloads) `high_52w`.

About 919 of 962 tickers have an overlay. Some delisted names 404 and are skipped. **0 Sectors credits.**

```bash
cd backend && PYTHONPATH=. python ../scripts/enrich_yahoo.py
```

---

## 10. Credits, without the scariness

We log every live Sectors call. `GET /api/credits` is the running counter.

Useful numbers:

- Structured `GET /v2/companies/` = **1 per page** (up to 200 rows). Natural language `q=` = **3**. We never use `q=`.
- `GET /v2/foreign-flow/` = **1 per page** (max 30 rows).
- `GET /v2/filings/` = **1 per page** (max 30 rows). Confirmed 21 Sept.
- HTTP **400** on a structured query is **free** (bad filter, nothing ran).
- Same URL + query already in `http_cache` = **0**.

Always `--dry-run` and `--max-credits` before a new snapshot. Paths we are allowed to call are listed in `backend/app/sectors/paths.py`. Do not guess new Sectors field names; check https://docs.sectors.app/llms.txt.

---

## 11. How to read the code as a beginner

Do this in order. Each step is one idea.

1. `backend/app/models/common.py` — `ScoreBreakdown` and `SignalBadge`. This is the contract.
2. `backend/app/services/signals.py` — four `if` rules. Easiest file in Phase 2.
3. `backend/app/services/scoring/types.py` — `StockInputs`. This is the “form” every method fills in.
4. `backend/app/services/scoring/methods/momentum.py` — shortest real method.
5. `backend/app/services/scoring/methods/composite.py` — how the four pillars become one number.
6. `backend/app/services/scoring/adapters/sectors.py` — where Sectors names become `StockInputs`.
7. `backend/app/services/anomalies.py` — two standard scores and their reasons.
8. `backend/app/sectors/where_clause.py` — the only place a user string turns into a paid query.
9. `backend/app/sectors/repository.py` — how the screener attaches score, badges and flags.

Tests are also documentation:

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. python -m pytest tests -q
```

Start with `tests/test_signals.py` and `tests/test_scoring_methods.py`. They use **synthetic** tickers (`MOVE.JK`, `SYN1.JK`), not live Sectors.

---

## 12. Mental model: null is allowed

| Situation | What you see |
|---|---|
| Watchlist or tiny market cap | Row exists, `overall_score` is `null` |
| Bank | No Piotroski / Magic Formula; quality from ROE among banks |
| No foreign-flow row that day | `flow_score` null; maybe unranked |
| No 12-1 and no daily change | `momentum_score` null |
| Daily move only +2% | No Mover badge |
| Net foreign inflow Rp 100 million | No accumulation badge (threshold is Rp 1B) |
| No insider buy in 30 days | No insider badge |
| Yahoo overlay saved before 22 Sept | No volume flag (no baseline stored yet) |
| Under 30 baseline sessions | No volume flag |
| Custom query match outside the snapshot | Row exists, score and badges empty |

`null` means “we did not compute this,” not “this stock is a zero.”

---

## 13. What we changed in the codebase (checklist)

**Scoring**

- New package `backend/app/services/scoring/`
- Routes `GET /api/scores` and `GET /api/scores/{symbol}`
- Screener `score` fields are nullable (`float | None`)
- Script `scripts/score_universe.py`

**Yahoo**

- Table `yahoo_price_overlay`
- Script `scripts/enrich_yahoo.py`

**Signals**

- `backend/app/services/signals.py`
- Tables `fifty_two_week_high_flags`, `insider_filings`
- Script `python -m app.sectors.signals_snapshot`
- `GET /api/screener?signal_filter=…`
- Stock detail includes `signals`

**Unusual activity**

- `backend/app/services/anomalies.py`
- `yahoo_price_overlay` columns `volume_average`, `volume_standard_deviation`, `volume_baseline_sessions`
- `GET /api/unusual` (was a stub returning an empty list)
- `GET /api/screener?anomaly_only=true`; rows carry `has_anomaly` and `anomalies`

**Custom logic**

- `backend/app/sectors/where_clause.py` (documented field list + validator)
- `GET /api/screener/custom` and `GET /api/screener/custom/fields`
- `GET /api/screener` rejects `filter_clause` and points at the billable route

**Glue**

- `repository.py` builds score + badges + anomaly flags for every cached company
- Derived rows are cached in memory; they rebuild when SQLite contents change
- `conftest.py` blanks `SECTORS_API_KEY`, so a test can never spend a real credit

**Docs / tests**

- `README.md` Score, Signals, Unusual activity and Custom logic sections
- `NOTES.md` credit log (remaining **915** after the 21 Sept snapshot)
- `project_brief.md` Phase 2 checkboxes
- Tests under `backend/tests/test_scoring_*.py`, `test_signals.py`, `test_yahoo_overlay.py`, `test_anomalies.py`, `test_custom_screener.py`

---

## 14. Common “wait, why?” questions

**Why not score from live Sectors on every page view?**  
Credits would vanish, and the app would be slow. Snapshot once, compute many times.

**Why Yahoo at all?**  
Phase 1 cache has no 12-month return. Yahoo is open market data for OHLCV only. Sectors remains the list of companies.

**Why is Quality often missing?**  
Piotroski needs last year’s financials. We have not paid the extra ~5 credits to snapshot `roa[2024]`, cash flow, NIM, NPL, `listing_date`. Composite still works with Value + Momentum + Flow (three parts).

**Why 5% / Rp 1B / 15% / 3 sigma / 8 sigma?**  
Those are our product rules, written as named constants at the top of `signals.py` and `anomalies.py`. Change them there, then re-run tests.

**Why does one flag say "standard deviations above its own average" and the other "above the IDX median"?**  
Volume has history in the cache; foreign flow has one day. The reason strings admit which comparison each one is.

**Is this investment advice?**  
No. Rankings, badges and flags are research tools for the hackathon demo.

---

## 15. What to study next (Phase 3)

1. Svelte UI: table with Score, Signal and Anomaly columns, plus the Unusual Activity tab.
2. The custom-logic box in the UI, wired to `/api/screener/custom/fields` so users pick valid fields.
3. Compare view for two or three candidates.

When those land, this file can get a sibling `learn_phase3.md`. Until then, Phase 2 is: **cache in, score, badges and flags out, never fake a number.**
