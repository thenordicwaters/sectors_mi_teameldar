from pydantic import BaseModel, Field

from app.models.common import ScoreBreakdown, SignalBadge


class StockOverview(BaseModel):
    listing_board: str | None = None
    industry: str | None = None
    sub_industry: str | None = None
    sector: str | None = None
    sub_sector: str | None = None
    market_cap: float | None = None
    market_cap_rank: int | None = None
    last_close_price: float | None = None
    daily_close_change: float | None = None
    listing_date: str | None = None
    tags: list[str] = Field(default_factory=list)
    indices: list[str] = Field(default_factory=list)


class StockValuation(BaseModel):
    pe_ttm: float | None = None
    pb_mrq: float | None = None
    ps_ttm: float | None = None
    forward_pe: float | None = None
    intrinsic_value: float | None = None


class StockFlow(BaseModel):
    net_foreign_inflow: float | None = None
    foreign_buy_idr: float | None = None
    foreign_sell_idr: float | None = None
    as_of: str | None = Field(default=None, description="YYYY-MM-DD")


class StockDetail(BaseModel):
    """Stock page. Company-report sections are fetched only when needed (1 credit each)."""

    symbol: str
    company_name: str
    overview: StockOverview
    valuation: StockValuation
    flow: StockFlow
    score: ScoreBreakdown
    signals: list[SignalBadge] = Field(default_factory=list)
    anomaly: bool = False
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )
