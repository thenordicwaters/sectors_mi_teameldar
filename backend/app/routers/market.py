from fastapi import APIRouter, HTTPException

from app.models.market import IndexSession, StockQuote
from app.sectors.database import get_database
from app.services.market_quotes import load_ihsg_session, load_stock_quote

router = APIRouter(prefix="/api", tags=["market"])


@router.get("/quotes/{ticker_symbol}", response_model=StockQuote)
def get_stock_quote(ticker_symbol: str) -> StockQuote:
    """Latest daily close from Yahoo Finance for one cached symbol. 0 Sectors credits."""
    normalized = _normalize_idx_symbol(ticker_symbol)
    row = get_database().execute(
        """
        SELECT last_close_price, fetched_at
        FROM company_universe
        WHERE ticker_symbol = ?
        """,
        (normalized,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{normalized} is not in the cached universe.")
    payload = load_stock_quote(
        normalized,
        snapshot_close=row["last_close_price"],
        snapshot_fetched_at=row["fetched_at"],
    )
    return StockQuote.model_validate(payload)


@router.get("/market/ihsg", response_model=IndexSession)
def get_ihsg() -> IndexSession:
    """Latest IHSG intraday session from Yahoo Finance. 0 Sectors credits."""
    return IndexSession.model_validate(load_ihsg_session())


def _normalize_idx_symbol(ticker_symbol: str) -> str:
    normalized = ticker_symbol.strip().upper()
    code = normalized[:-3] if normalized.endswith(".JK") else normalized
    if len(code) != 4 or not code.isalpha():
        raise HTTPException(status_code=400, detail="IDX symbol must be 4 letters.")
    return f"{code}.JK"
