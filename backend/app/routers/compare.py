from fastapi import APIRouter, HTTPException, Query

from app.models.compare import CompareResponse

router = APIRouter(prefix="/api/compare", tags=["compare"])


@router.get("", response_model=CompareResponse)
def compare_stocks(
    ticker_symbols: str = Query(
        ..., description="Comma-separated, 2 or 3 IDX ticker symbols."
    ),
) -> CompareResponse:
    """Stub until Phase 2 fills metrics from cached rows."""
    raw_symbols = ticker_symbols.split(",")
    normalized_symbols = [
        ticker.strip().upper().removesuffix(".JK")
        for ticker in raw_symbols
        if ticker.strip()
    ]
    if not (2 <= len(normalized_symbols) <= 3):
        raise HTTPException(status_code=400, detail="Compare 2 or 3 symbols.")
    symbols_with_exchange_suffix = [
        f"{ticker}.JK" for ticker in normalized_symbols
    ]
    return CompareResponse(
        ticker_symbols=symbols_with_exchange_suffix,
        company_names={
            ticker: "" for ticker in symbols_with_exchange_suffix
        },
        metrics=[],
    )
