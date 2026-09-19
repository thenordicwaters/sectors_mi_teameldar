from pydantic import BaseModel, Field

from app.models.common import Pagination, ScoreBreakdown, SignalBadge, ViewTab


class ScreenerQuery(BaseModel):
    """Incoming screener request. `filter_clause` is a Sectors structured where clause (1 credit)."""

    filter_clause: str | None = Field(
        default=None,
        description="Sectors structured where clause. Credit cost: 1 per page.",
    )
    sort_by: str = Field(
        default="-overall_score",
        description="Sort field; prefix with - for descending.",
    )
    view_tab: ViewTab = ViewTab.overview
    signal_filter: str | None = None
    page_size: int = Field(default=20, ge=1, le=200)
    page_offset: int = Field(default=0, ge=0)


class ScreenerRow(BaseModel):
    """One table row. Finviz-style density plus Score / Signal / Anomaly."""

    ticker_symbol: str
    company_name: str
    sector: str | None = None
    sub_sector: str | None = None
    last_close_price: float | None = None
    daily_close_change: float | None = Field(
        default=None, description="Decimal, e.g. -0.02 = -2%."
    )
    market_capitalization: float | None = None
    price_to_earnings_trailing_twelve_months: float | None = None
    price_to_book_most_recent_quarter: float | None = None
    price_to_sales_trailing_twelve_months: float | None = None
    return_on_equity_trailing_twelve_months: float | None = None
    dividend_yield_trailing_twelve_months: float | None = None
    net_foreign_inflow: float | None = Field(
        default=None, description="Rupiah, latest cached trading day."
    )
    volume: float | None = None
    score: ScoreBreakdown
    signals: list[SignalBadge] = Field(default_factory=list)
    has_anomaly: bool = False


class ScreenerResponse(BaseModel):
    results: list[ScreenerRow]
    pagination: Pagination
    view_tab: ViewTab
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )
