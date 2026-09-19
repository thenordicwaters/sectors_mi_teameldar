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

API contract lives in `backend/app/models/`. Stubs return empty results until Phase 1 loads a cached snapshot. Do not invent numbers.

## Score

Formula and weights: TBD in Phase 2 (value, quality, momentum, flow). Each stock will show a breakdown of why it ranks where it does.
