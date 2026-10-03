from typing import Literal

from pydantic import BaseModel, Field

SessionStatus = Literal["today", "weekend", "earlier", "unavailable"]


class IntradayPoint(BaseModel):
    time: str
    price: float


class StockQuote(BaseModel):
    """Latest session for one cached IDX symbol. Yahoo Finance, 0 Sectors credits."""

    ticker_symbol: str
    close: float | None = None
    previous_close: float | None = None
    change: float | None = None
    session_date: str | None = Field(default=None, description="YYYY-MM-DD")
    session_status: SessionStatus = "unavailable"
    snapshot_close: float | None = None
    snapshot_fetched_at: str | None = Field(
        default=None,
        description="When the Sectors universe snapshot stored snapshot_close.",
    )
    prior_session_date: str | None = Field(
        default=None,
        description="Previous trading session, H-1, as YYYY-MM-DD.",
    )
    prior_high: float | None = Field(
        default=None,
        description="Highest price on the previous trading session.",
    )
    points: list[IntradayPoint] = Field(default_factory=list)
    source: str = "Yahoo Finance"


PriceRange = Literal["1m", "3m", "1y", "all"]


class HistoryPoint(BaseModel):
    date: str = Field(description="YYYY-MM-DD")
    close: float


class PriceHistory(BaseModel):
    """Daily closes through the previous Jakarta date. Not a live session."""

    symbol: str
    name: str
    range: PriceRange
    as_of_date: str = Field(description="Yesterday in Asia/Jakarta, YYYY-MM-DD.")
    session_date: str | None = Field(
        default=None,
        description="Date of the last close on or before as_of_date.",
    )
    close: float | None = None
    previous_close: float | None = None
    change: float | None = None
    points: list[HistoryPoint] = Field(default_factory=list)
    source: str = "Sectors"


class IndexSession(BaseModel):
    """Latest IHSG session. Yahoo Finance symbol ^JKSE, 0 Sectors credits."""

    symbol: str = "^JKSE"
    name: str = "IHSG"
    session_date: str | None = Field(default=None, description="YYYY-MM-DD")
    session_status: SessionStatus = "unavailable"
    last_price: float | None = None
    previous_close: float | None = None
    change: float | None = None
    prior_session_date: str | None = None
    prior_high: float | None = None
    points: list[IntradayPoint] = Field(default_factory=list)
    source: str = "Yahoo Finance"
