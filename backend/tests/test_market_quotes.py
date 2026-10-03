from datetime import date

import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.sectors.database import get_database
from app.services.market_quotes import (
    classify_session,
    session_view_from_frames,
)

api_client = TestClient(app)


def test_weekend_uses_the_previous_session() -> None:
    assert classify_session(date(2026, 10, 2), date(2026, 10, 3)) == "weekend"
    assert classify_session(date(2026, 10, 2), date(2026, 10, 2)) == "today"
    assert classify_session(date(2026, 10, 1), date(2026, 10, 2)) == "earlier"


def test_session_view_uses_official_close_and_previous_day_high() -> None:
    daily = pd.DataFrame(
        {
            "High": [6200.0, 6150.0, 6150.0],
            "Close": [6075.0, 6000.0, 6100.0],
        },
        index=pd.to_datetime(["2026-09-30", "2026-10-01", "2026-10-02"]),
    )
    intraday = pd.DataFrame(
        {"Close": [6000.0, 6050.0, 6080.0]},
        index=pd.to_datetime(
            ["2026-10-02 09:00", "2026-10-02 09:05", "2026-10-02 15:55"]
        ).tz_localize("Asia/Jakarta"),
    )
    view = session_view_from_frames(intraday, daily)
    assert view is not None
    assert view["session_date"] == "2026-10-02"
    assert view["close"] == 6100.0
    assert view["previous_close"] == 6000.0
    assert view["prior_session_date"] == "2026-10-01"
    assert view["prior_high"] == 6150.0
    assert len(view["points"]) == 3
    assert view["points"][0]["price"] == 6000.0


def test_multiindex_daily_still_finds_the_previous_high() -> None:
    index = pd.to_datetime(["2026-10-01", "2026-10-02"])
    columns = pd.MultiIndex.from_product([["High", "Close"], ["BBCA.JK"]])
    daily = pd.DataFrame([[6150.0, 6000.0], [6150.0, 6100.0]], index=index, columns=columns)
    view = session_view_from_frames(pd.DataFrame(), daily)
    assert view is not None
    assert view["close"] == 6100.0
    assert view["prior_high"] == 6150.0
    assert view["points"] == []


def test_quote_route_returns_session_and_snapshot(monkeypatch) -> None:
    _insert_company("BBCA.JK")
    monkeypatch.setattr(
        "app.services.market_quotes.jakarta_today",
        lambda: date(2026, 10, 3),
    )
    monkeypatch.setattr(
        "app.services.market_quotes.download_daily",
        lambda symbol: _daily_frame(),
    )
    monkeypatch.setattr(
        "app.services.market_quotes.download_intraday",
        lambda symbol: _intraday_frame(),
    )

    response = api_client.get("/api/quotes/BBCA")
    assert response.status_code == 200
    body = response.json()
    assert body["close"] == 6100.0
    assert body["session_date"] == "2026-10-02"
    assert body["session_status"] == "weekend"
    assert body["prior_high"] == 6150.0
    assert body["prior_session_date"] == "2026-10-01"
    assert body["snapshot_close"] == 6300.0
    assert body["points"]

    cached = api_client.get("/api/quotes/bbca")
    assert cached.json()["close"] == 6100.0


def test_quote_route_rejects_unknown_symbols() -> None:
    assert api_client.get("/api/quotes/NOPE").status_code == 404
    assert api_client.get("/api/quotes/BB").status_code == 400


def _daily_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {"High": [6150.0, 6150.0], "Close": [6000.0, 6100.0]},
        index=pd.to_datetime(["2026-10-01", "2026-10-02"]),
    )


def _intraday_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {"Close": [6010.0, 6100.0]},
        index=pd.to_datetime(["2026-10-02 09:00", "2026-10-02 15:55"]).tz_localize("Asia/Jakarta"),
    )


def _insert_company(symbol: str) -> None:
    get_database().execute(
        """
        INSERT INTO company_universe (
            ticker_symbol, company_name, sector, sub_sector, listing_board,
            last_close_price, daily_close_change, market_capitalization,
            market_capitalization_rank,
            price_to_earnings_trailing_twelve_months,
            price_to_book_most_recent_quarter,
            price_to_sales_trailing_twelve_months,
            return_on_equity_trailing_twelve_months,
            dividend_yield_trailing_twelve_months,
            query_values_json, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            symbol,
            "Bank Central Asia",
            "Financials",
            "Banks",
            "Main",
            6300,
            -0.01,
            700_000_000_000_000,
            1,
            20,
            4,
            8,
            0.2,
            0.03,
            "{}",
            "2026-09-19T15:06:28+00:00",
        ),
    )
