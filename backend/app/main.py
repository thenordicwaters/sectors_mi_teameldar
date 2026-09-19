from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import compare, screener, stocks, unusual

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
app.include_router(stocks.router)
app.include_router(compare.router)
app.include_router(unusual.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "disclaimer": DISCLAIMER}
