# Build notes

Information and analysis only. Not investment advice.

## Repo

- GitHub: https://github.com/thenordicwaters/sectors_mi_teameldar
- Local folder: `sectors_api` (working title TBD)
- Stack: FastAPI (`backend/`) + SvelteKit / Svelte 5 (`frontend/`)

## Sectors v2 (do not guess paths)

Base: `https://api.sectors.app/v2`  
Auth: `Authorization` header with the API key. Docs index: https://docs.sectors.app/llms.txt

| Our need | Sectors path | Credit cost |
|---|---|---|
| Screener universe / custom `where` | `GET /v2/companies/` structured (`where`, `order_by`, `limit`≤200) | **1** per page |
| Plain-English screener (`q`) | same path, `q=` | **3** (avoid in Phase 1–3) |
| Company report | `GET /v2/company/report/{symbol}/` | **1 per section**, 8 if all |
| Full-universe foreign flow | `GET /v2/foreign-flow/` | **1 per page** (max `limit` 30; ~20–25 pages for the universe) |
| Top movers | `GET /v2/companies/top-changes/` (confirm exact path before calling) | unknown until first call — log it |
| Insider filings | news/filings endpoint (confirm path before calling) | unknown until first call |

Billing reminders from docs:

- 2xx: billed at the endpoint cost
- 404 unknown symbol: **1** credit
- 400 structured query: **free**
- 429 / 401 / 5xx: **free**
- Never loop the market with per-stock report calls

## Credit log

Start: 1,000. Budget: ~300 dev, ~200 snapshots, ~500 reserve.

| Date | Endpoint | Pages/sections | Credits | Remaining | Notes |
|---|---|---|---|---|---|
| | | | | 1000 | none yet |

## Phase 0 contract

Our app owns the response shapes in `backend/app/models/`. Sectors payloads are mapped in later phases; the frontend should only talk to `/api/*`.
