from pydantic import BaseModel, Field

from app.models.common import Pagination, ScoreBreakdown, SignalBadge, ViewTab


class ScreenerQuery(BaseModel):
    """Incoming screener request. `where` is a Sectors structured clause (1 credit)."""

    where: str | None = Field(
        default=None,
        description="Sectors structured where clause. Credit cost: 1 per page.",
    )
    order_by: str = Field(default="-score", description="Sort field; prefix - for desc.")
    view: ViewTab = ViewTab.overview
    signal: str | None = None
    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class ScreenerRow(BaseModel):
    """One table row. Finviz-style density plus Score / Signal / Anomaly."""

    symbol: str
    company_name: str
    sector: str | None = None
    sub_sector: str | None = None
    last_close_price: float | None = None
    daily_close_change: float | None = Field(
        default=None, description="Decimal, e.g. -0.02 = -2%."
    )
    market_cap: float | None = None
    pe_ttm: float | None = None
    pb_mrq: float | None = None
    ps_ttm: float | None = None
    roe_ttm: float | None = None
    yield_ttm: float | None = None
    net_foreign_inflow: float | None = Field(
        default=None, description="IDR, latest cached trading day."
    )
    volume: float | None = None
    score: ScoreBreakdown
    signals: list[SignalBadge] = Field(default_factory=list)
    anomaly: bool = False


class ScreenerResponse(BaseModel):
    results: list[ScreenerRow]
    pagination: Pagination
    view: ViewTab
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )
