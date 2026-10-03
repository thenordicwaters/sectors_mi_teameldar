import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import compare, credits, market, scores, screener, stocks, unusual
from app.sectors.daily_refresh import schedule_daily_refresh

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)

DISCLAIMER = "Information and analysis only. Not investment advice."

app = FastAPI(
    title="IDX Screener API",
    version="0.1.0",
    description=DISCLAIMER,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(screener.router)
app.include_router(scores.router)
app.include_router(stocks.router)
app.include_router(market.router)
app.include_router(compare.router)
app.include_router(unusual.router)
app.include_router(credits.router)


@app.middleware("http")
async def start_daily_refresh(request, call_next):
    if request.url.path.startswith("/api"):
        schedule_daily_refresh()
    return await call_next(request)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "disclaimer": DISCLAIMER}
