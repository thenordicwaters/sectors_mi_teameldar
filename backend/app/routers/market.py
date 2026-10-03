from fastapi import APIRouter, HTTPException, Query

from app.models.market import IndexSession, PriceHistory, StockQuote
from app.sectors.client import SectorsClient, SectorsCreditBudgetError
from app.sectors.database import get_database
from app.services.market_quotes import load_ihsg_session, load_stock_quote
from app.services.price_history import PRICE_RANGES, load_index_history, load_price_history

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


@router.get("/market/ihsg/history", response_model=PriceHistory)
def get_ihsg_history(range_key: str = Query(default="3m", alias="range")) -> PriceHistory:
    """IHSG daily closes from Sectors through yesterday.

    1 credit per 90-day window, or 0 when that exact window is already cached.
    The window ending yesterday is requested again on the next Jakarta date.
    """
    _require_range(range_key)
    return _history_response(load_index_history, range_key)


@router.get("/market/history/{ticker_symbol}", response_model=PriceHistory)
def get_symbol_history(
    ticker_symbol: str,
    range_key: str = Query(default="3m", alias="range"),
) -> PriceHistory:
    """One symbol's daily closes from Sectors through yesterday.

    1 credit per 90-day window, or 0 on a cache hit. Unknown symbols are
    rejected locally and do not call Sectors.
    """
    normalized = _normalize_idx_symbol(ticker_symbol)
    _require_range(range_key)
    row = get_database().execute(
        "SELECT company_name FROM company_universe WHERE ticker_symbol = ?",
        (normalized,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{normalized} is not in the cached universe.")

    def load(range_name: str, *, client: SectorsClient) -> dict:
        return load_price_history(
            kind="stock",
            symbol=normalized.split(".", 1)[0],
            name=row["company_name"],
            range_key=range_name,
            client=client,
        )

    return _history_response(load, range_key)


def _require_range(range_key: str) -> None:
    if range_key not in PRICE_RANGES:
        raise HTTPException(status_code=400, detail="Range must be 1m, 3m, 1y, or all.")


def _history_response(load, range_key: str) -> PriceHistory:
    client = SectorsClient()
    try:
        payload = load(range_key, client=client)
    except SectorsCreditBudgetError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    finally:
        client.close()
    return PriceHistory.model_validate(payload)


def _normalize_idx_symbol(ticker_symbol: str) -> str:
    normalized = ticker_symbol.strip().upper()
    code = normalized[:-3] if normalized.endswith(".JK") else normalized
    if len(code) != 4 or not code.isalpha():
        raise HTTPException(status_code=400, detail="IDX symbol must be 4 letters.")
    return f"{code}.JK"
