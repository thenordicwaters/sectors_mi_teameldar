from fastapi import APIRouter, HTTPException

from app.models.stock import StockDetail, StockFlow, StockOverview, StockValuation
from app.sectors.repository import get_screener_row

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/{ticker_symbol}", response_model=StockDetail)
def get_stock_detail(ticker_symbol: str) -> StockDetail:
    """Cached universe row plus derived score and signal badges. 0 Sectors credits."""
    row = get_screener_row(ticker_symbol)
    if row is None:
        normalized = ticker_symbol.strip().upper()
        if not normalized.endswith(".JK"):
            normalized = f"{normalized}.JK"
        if len(normalized.removesuffix(".JK")) != 4 or not normalized.removesuffix(".JK").isalpha():
            raise HTTPException(status_code=400, detail="IDX symbol must be 4 letters.")
        raise HTTPException(status_code=404, detail=f"{normalized} is not in the cached universe.")
    return StockDetail(
        ticker_symbol=row.ticker_symbol,
        company_name=row.company_name,
        overview=StockOverview(
            sector=row.sector,
            sub_sector=row.sub_sector,
            market_capitalization=row.market_capitalization,
            last_close_price=row.last_close_price,
            daily_close_change=row.daily_close_change,
        ),
        valuation=StockValuation(
            price_to_earnings_trailing_twelve_months=row.price_to_earnings_trailing_twelve_months,
            price_to_book_most_recent_quarter=row.price_to_book_most_recent_quarter,
            price_to_sales_trailing_twelve_months=row.price_to_sales_trailing_twelve_months,
        ),
        flow=StockFlow(net_foreign_inflow=row.net_foreign_inflow),
        score=row.score,
        signals=row.signals,
        has_anomaly=row.has_anomaly,
        anomalies=row.anomalies,
    )
