from fastapi import APIRouter, HTTPException

from app.models.common import ScoreBreakdown
from app.models.stock import StockDetail, StockFlow, StockOverview, StockValuation

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/{symbol}", response_model=StockDetail)
def get_stock(symbol: str) -> StockDetail:
    """Stub. Phase 1 will map cached company-report sections (1 credit each)."""
    cleaned = symbol.strip().upper().removesuffix(".JK")
    if len(cleaned) != 4 or not cleaned.isalpha():
        raise HTTPException(status_code=400, detail="IDX symbol must be 4 letters.")
    return StockDetail(
        symbol=f"{cleaned}.JK",
        company_name="",
        overview=StockOverview(),
        valuation=StockValuation(),
        flow=StockFlow(),
        score=ScoreBreakdown(
            overall=0, value=0, quality=0, momentum=0, flow=0, rank=None
        ),
    )
