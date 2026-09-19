from fastapi import APIRouter, HTTPException

from app.models.common import ScoreBreakdown
from app.models.stock import StockDetail, StockFlow, StockOverview, StockValuation

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/{ticker_symbol}", response_model=StockDetail)
def get_stock_detail(ticker_symbol: str) -> StockDetail:
    """Stub. Phase 1 will map cached company-report sections (1 credit each)."""
    normalized_symbol = ticker_symbol.strip().upper().removesuffix(".JK")
    if len(normalized_symbol) != 4 or not normalized_symbol.isalpha():
        raise HTTPException(status_code=400, detail="IDX symbol must be 4 letters.")
    return StockDetail(
        ticker_symbol=f"{normalized_symbol}.JK",
        company_name="",
        overview=StockOverview(),
        valuation=StockValuation(),
        flow=StockFlow(),
        score=ScoreBreakdown(
            overall_score=0,
            value_score=0,
            quality_score=0,
            momentum_score=0,
            flow_score=0,
            universe_rank=None,
        ),
    )
