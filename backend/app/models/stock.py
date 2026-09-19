from pydantic import BaseModel, Field

from app.models.common import ScoreBreakdown, SignalBadge


class StockOverview(BaseModel):
    listing_board: str | None = None
    industry: str | None = None
    sub_industry: str | None = None
    sector: str | None = None
    sub_sector: str | None = None
    market_capitalization: float | None = None
    market_capitalization_rank: int | None = None
    last_close_price: float | None = None
    daily_close_change: float | None = None
    listing_date: str | None = None
    tags: list[str] = Field(default_factory=list)
    indices: list[str] = Field(default_factory=list)


class StockValuation(BaseModel):
    price_to_earnings_trailing_twelve_months: float | None = None
    price_to_book_most_recent_quarter: float | None = None
    price_to_sales_trailing_twelve_months: float | None = None
    forward_price_to_earnings: float | None = None
    intrinsic_value: float | None = None


class StockFlow(BaseModel):
    net_foreign_inflow: float | None = None
    foreign_buy_value_rupiah: float | None = None
    foreign_sell_value_rupiah: float | None = None
    as_of_date: str | None = Field(default=None, description="YYYY-MM-DD")


class StockDetail(BaseModel):
    """Stock page. Company-report sections are fetched only when needed (1 credit each)."""

    ticker_symbol: str
    company_name: str
    overview: StockOverview
    valuation: StockValuation
    flow: StockFlow
    score: ScoreBreakdown
    signals: list[SignalBadge] = Field(default_factory=list)
    has_anomaly: bool = False
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )
