from pydantic import BaseModel, Field

from app.models.anomalies import AnomalyFlag
from app.models.common import Pagination, ScoreBreakdown, SignalBadge, ViewTab


class ScreenerQuery(BaseModel):
    """Incoming screener request for the cached snapshot (0 credits)."""

    filter_clause: str | None = Field(
        default=None,
        description=(
            "Rejected here. Send a Sectors where clause to /api/screener/custom, "
            "which costs 1 credit per page."
        ),
    )
    sort_by: str = Field(
        default="-overall_score",
        description="Sort field; prefix with - for descending.",
    )
    view_tab: ViewTab = ViewTab.overview
    signal_filter: str | None = Field(
        default=None,
        description="Keep rows that already have this badge: mover, fifty_two_week_high, foreign_accumulation, insider_buying.",
    )
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
    anomalies: list[AnomalyFlag] = Field(default_factory=list)


class ScreenerResponse(BaseModel):
    results: list[ScreenerRow]
    pagination: Pagination
    view_tab: ViewTab
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )


class CustomScreenerResponse(BaseModel):
    """Result of a validated `where` clause sent live to Sectors. 1 credit per page."""

    where_clause: str = Field(description="The clause after validation, as sent to Sectors.")
    order_by: str
    results: list[ScreenerRow]
    pagination: Pagination
    credits_charged: int = Field(
        ge=0, description="0 when this exact query was already cached."
    )
    cache_hit: bool
    scored_from_cache: int = Field(
        ge=0,
        description="Matches that also exist in the snapshot, so they carry Score and Signals.",
    )
    notes: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )


class ScreenerFieldsResponse(BaseModel):
    """What the custom-logic box accepts. Serving this list costs 0 credits."""

    operators: list[str]
    logic_keywords: list[str]
    direct_fields: list[str]
    array_fields: list[str]
    latest_value_fields: list[str]
    yearly_fields: list[str] = Field(description="Use bracket notation, e.g. roe[2024].")
    quarterly_fields: list[str] = Field(
        description="Use bracket notation, e.g. revenue_q[Q1-2024]."
    )
    examples: list[str]
    max_clause_length: int
    max_conditions: int
    credits_per_page: int
