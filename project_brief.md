# Project Brief: Finviz-style IDX Screener (Sectors Hackathon 2026)

> Written for two readers: me (the builder) and my AI coding assistant. If you are the AI, read the whole file before writing any code, then follow the rules in section 8.

## 1. Where we are

I am entering the **Sectors Hackathon 2026** on the **Market Intelligence** track. Status as of **Saturday 19 Sept 2026**:

- [x] Team registered and Sectors onboarding completed
- [x] 1,000 Sectors API credits claimed
- [x] API key generated
- [x] Stack chosen: **Python FastAPI** backend + **SvelteKit** frontend
- [ ] Repository not created yet (must be created inside the build period)

Team size: **solo** (assumption, edit if wrong). Working title: *TBD*.

## 2. Links

| What | Link |
|---|---|
| Official rules | https://hackathon.sectors.app/rules |
| Track page (Market Intelligence) | https://hackathon.sectors.app/tracks/market-intelligence |
| Submission portal | https://hackathon.sectors.app/portal/submit |
| Team portal (credits) | https://hackathon.sectors.app/portal/team |
| Sectors API page (keys) | https://sectors.app/api |
| API docs index (all pages) | https://docs.sectors.app/llms.txt |
| Screener reference | https://docs.sectors.app/api-references/v2/indonesia/screener/companies |
| Company report reference | https://docs.sectors.app/api-references/v2/indonesia/report/company-report |
| Anomaly detection recipe (optional inspiration) | https://docs.sectors.app/recipes/gnn-anomaly-detection/01-gnn-part-1.md |
| Design reference | https://finviz.com/screener |
| Help / questions | Hackathon Slack: `#discussion` (rules), `#support` (problems) |

## 3. Time limit

| Milestone | Date |
|---|---|
| Registration closes | 22 Sept 2026, 23:59 WIB |
| **Build and submissions close** | **30 Sept 2026, 23:59 WIB** |
| Judging (asynchronous, from materials only) | 1 to 8 Oct 2026 |
| Winners announced | 9 Oct 2026 |

About 11 days of build time remain. **Code freezes at the moment of submission** (or the deadline): no commits, bug fixes or edits after that, or the team is disqualified. Plan to submit on **29 Sept**, keeping 30 Sept as buffer only.

## 4. Constraints (from the official rules)

1. **Sectors must be core.** The product must lose its main function if Sectors data is removed. One decorative call does not count.
2. **Derived insight is mandatory.** A product that only shows raw Sectors data in a different visual form does not qualify for this track, however well presented. Qualifying ideas: signals or scores, rankings, screeners with custom logic, anomaly detection, comparative analysis, synthesized research. An AI/LLM component is optional for this track.
3. **Working end to end.** Rough edges are fine; a product that does not work fails judging. Live deployment is not required.
4. **Fresh code only.** The repository must be created during the build period (from 19 Aug). No code from previous projects. No code before 19 Aug.
5. **No automated trading.** Analyze, screen, score and alert only. Never place or automate buy/sell orders, and do not connect brokerage accounts.
6. **No financial advice.** Position the app as an information and analysis tool, with a visible disclaimer.
7. **Third-party sources are allowed** (stack, tools and languages are unrestricted), as long as Sectors stays the core data source.
8. **Credits:** 1,000 total, exclusively for this project. Registering extra accounts for more credits is grounds for disqualification.
9. **AI coding tools are fully permitted**, with no disclosure required.

## 5. How we will be judged

| Criterion | Weight | What it means for us |
|---|---|---|
| Real-world usability | 40% | Someone can use it today and benefit. A screener with a useful, explained score |
| Video demo and storytelling | 30% | A clear problem, a real audience, a smooth end-to-end demo |
| Technical depth and execution | 30% | Verified against the repo: real, functional, not faked, smart use of Sectors data |

Judging is asynchronous, so the video and repository must speak for themselves.

## 6. The story (this is also the video script)

**Who:** an Indonesian retail investor who screens stocks by hand, hopping between tabs and spreadsheets, with no clear way to tell which stocks stand out today.

**Problem:** Indonesian market data is deep, but raw numbers do not tell you what deserves attention. Finviz solved this for US stocks with a fast, dense screener. Nothing comparable exists for the IDX (Indonesia Stock Exchange) that also explains *why* a stock ranks well.

**Our product:** a Finviz-style screener for IDX stocks built on Sectors data. It adds three things Finviz-style tables usually lack:
1. A transparent **Score** (value, quality, momentum, flow) with a per-stock breakdown, so users see why a stock ranks where it does.
2. **Signals and unusual-activity flags**, such as foreign accumulation or abnormal volume, each with a stated reason.
3. A **Compare** view that puts two or three candidates side by side.

**Demo storyline (3 minutes):**
1. 0:00 to 0:30, the problem, in one sentence
2. 0:30 to 1:15, open the screener, apply filters, sort by Score
3. 1:15 to 1:45, custom-logic box: a custom query narrows the list
4. 1:45 to 2:15, the Unusual Activity tab, with reasons
5. 2:15 to 2:45, click a stock, then Compare with two peers
6. 2:45 to 3:00, how Sectors powers everything, plus the disclaimer

**One-sentence problem statement (draft):** For Indonesian retail investors who screen stocks by hand, a Finviz-style screener that ranks IDX stocks with a transparent score, flags unusual foreign-flow and volume activity, and compares candidates side by side.

## 7. Design spec (Finviz style)

Copy the layout, not the data. Layout elements:
- Top bar with navigation and a light/dark toggle
- Control row: presets, order-by, and a Signal dropdown
- Tabbed filter grid of small dropdowns
- View tabs that swap table columns: **Overview, Valuation, Flow**
- Result bar showing the match count
- Dense table, 20 rows per page, green/red change coloring, numbered pagination
- Extra tabs: **Compare** and **Unusual Activity**
- **Derived columns Finviz does not have:** Score, Signal badges, Anomaly flag

## 8. Rules for the AI assistant

- Keep secrets out of git: the API key lives in `.env`, which is in `.gitignore`. Never print or commit it.
- Backend: FastAPI, `httpx`, pandas, SQLite cache. Frontend: SvelteKit using **Svelte 5** syntax (runes), TypeScript, Tailwind CSS. Generate frontend types from FastAPI's OpenAPI schema.
- Use Sectors API **v2** (`https://api.sectors.app/v2`, key sent in the `Authorization` header). v1 is discontinued. Get exact endpoint paths from `https://docs.sectors.app/llms.txt` and the schema it links; never guess a path.
- **Credit discipline:** before adding any Sectors call, state its credit cost. Known costs: structured screener query 1 credit (up to 200 rows per page), plain-English screener query 3, company report 1 per section (8 for a full report), unknown symbol (404) 1, bad request (400) free. Cache every response and develop against the cache. Never loop over the whole market with per-stock calls.
- Show a running credit counter in the backend logs.
- No fake data. Cached real responses are fine; invented numbers are not.
- Never add trade execution or brokerage connections.
- Add the disclaimer to the UI and README: information and analysis only, not investment advice.
- Third-party sources (for example Yahoo Finance for open/high/low/close prices, an LLM API for summaries) may support the app but must never replace Sectors as the core.
- Work in small steps: one task, show what changed, wait for review.

## 9. Credit budget (1,000 credits)

| Use | Credits |
|---|---|
| Development and testing | about 300 |
| Demo data snapshots | about 200 |
| Reserve | about 500 |

## 10. Todo list

**Phase 0: Setup (19 Sept)**
- [x] **[Me]** Register, onboard, claim credits, generate key
- [x] **[Me]** Choose stack (FastAPI + SvelteKit)
- [x] **[AI]** Create fresh repo with `/backend` and `/frontend`, `.gitignore`, `.env.example`, and a notes file
- [x] **[AI]** Define the API contract first: Pydantic models for screener rows, stock detail, compare and anomalies

**Phase 1: Data layer (19 to 20 Sept)**
- [x] **[AI]** Sectors client with caching, retry, 429 handling and a credit counter
- [x] **[AI]** Snapshot script: screener universe and full-universe foreign flow into SQLite
- [x] **[Me]** Check the credit counter and note each endpoint's real cost

**Phase 2: Derived insight (21 to 24 Sept), the part that qualifies**
- [x] **[Me]** Decide the score formula and weights, and be ready to explain them on video
- [x] **[AI]** Score and ranking with a per-stock breakdown
- [x] **[AI]** Signal badges from Sectors data (movers, 52-week high, foreign accumulation, insider buying)
- [x] **[AI]** Unusual-activity detection (z-scores on volume and foreign flow) with a reason per flag
- [x] **[AI]** Custom-logic endpoint that passes a validated `where` query to Sectors' screener

**Phase 3: Finviz-style UI (22 to 26 Sept)**
- [ ] **[AI]** Routes: `/` (screener), `/stock/[symbol]`, `/compare`, `/unusual`
- [ ] **[AI]** Control row, filter grid, sortable table with Score, Signal and Anomaly columns
- [ ] **[Me]** Click through it on real data and list what feels wrong

**Phase 4: Submission (28 to 29 Sept)**
- [ ] **[Me]** Record the 1-minute teaser (public on YouTube or social media)
- [ ] **[Me]** Record the judging video (up to 3 minutes)
- [ ] **[AI]** README: how Sectors powers the core, setup steps, score formula, disclaimer
- [ ] **[Me]** Social media post on Instagram, LinkedIn, Threads or TikTok, tagging Sectors and using the thumbnail template (https://canva.link/mexgt4g89m17xln)
- [ ] **[Me]** Remove all API keys, make the repo public, submit through the portal with the problem statement, track and participant names
- [ ] **[Me]** Keep the repo public for at least 90 days after winners are announced (until about 7 Jan 2027), or prize eligibility is lost

## 11. Cut list (in this order, if time runs short)

1. LLM summary
2. Dark mode and saved filter sets
3. Plain-English screening
4. Extra view tabs

**Never cut:** the Score, the signals, the Unusual Activity tab, the video, and the README.