from datetime import date, timedelta

import httpx
import pytest

from app.config import settings
from app.sectors.client import SectorsClient
from app.sectors.credits import credits_used
from app.sectors.database import get_database
from app.services.price_history import (
    chart_as_of,
    load_index_history,
    load_price_history,
    windows_for_range,
)
from fastapi.testclient import TestClient

from app.main import app

api_client = TestClient(app)


def test_chart_ends_on_the_previous_jakarta_date() -> None:
    assert chart_as_of(date(2026, 10, 3)) == date(2026, 10, 2)


def test_short_ranges_share_one_cached_window_and_stop_yesterday(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        start = request.url.params["start"]
        end = request.url.params["end"]
        calls.append((start, end))
        assert end <= "2026-10-02"
        rows = _index_rows(start, end)
        rows.append({"index_code": "IHSG", "date": "2026-10-03", "price": 9999})
        return httpx.Response(200, json=rows)

    client = SectorsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    three_months = load_index_history("3m", today=date(2026, 10, 3), client=client)
    spent = credits_used()
    assert three_months["as_of_date"] == "2026-10-02"
    assert three_months["session_date"] == "2026-10-02"
    assert three_months["source"] == "Sectors"
    assert three_months["points"][-1]["date"] == "2026-10-02"
    assert all(point["date"] <= "2026-10-02" for point in three_months["points"])
    assert three_months["points"][0]["date"] >= "2026-07-05"

    one_month = load_index_history("1m", today=date(2026, 10, 3), client=client)
    assert credits_used() == spent
    assert one_month["points"][0]["date"] >= "2026-09-02"
    assert one_month["points"][-1]["date"] == "2026-10-02"
    assert len(one_month["points"]) > 2
    assert len(calls) == len(windows_for_range("3m", date(2026, 10, 2)))


def test_next_jakarta_day_refetches_only_the_open_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")
    calls: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        start = request.url.params["start"]
        end = request.url.params["end"]
        calls.append((start, end))
        return httpx.Response(200, json=_index_rows(start, end))

    client = SectorsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    load_index_history("all", today=date(2026, 10, 3), client=client)
    first_call_count = len(calls)
    spent = credits_used()
    assert calls[0][0] == "2019-01-02"
    assert calls[-1][1] == "2026-10-02"

    load_index_history("all", today=date(2026, 10, 3), client=client)
    assert len(calls) == first_call_count
    assert credits_used() == spent

    load_index_history("all", today=date(2026, 10, 4), client=client)
    fresh_calls = calls[first_call_count:]
    assert len(fresh_calls) == 1
    assert fresh_calls[0][1] == "2026-10-03"
    assert credits_used() == spent + 1


def test_stock_history_uses_sectors_daily_for_the_cached_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")
    _insert_company("BBCA.JK")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v2/daily/BBCA/")
        start = request.url.params["start"]
        end = request.url.params["end"]
        return httpx.Response(200, json=_stock_rows(start, end))

    client = SectorsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    history = load_price_history(
        kind="stock",
        symbol="BBCA",
        name="Bank Central Asia",
        range_key="1m",
        today=date(2026, 10, 3),
        client=client,
    )
    assert history["symbol"] == "BBCA.JK"
    assert history["session_date"] == "2026-10-02"
    assert history["source"] == "Sectors"
    assert history["points"][0]["date"] >= "2026-09-02"


def test_empty_sectors_window_falls_back_to_yahoo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[])

    monkeypatch.setattr(
        "app.services.price_history._yahoo_bars",
        lambda kind, symbol, start, end: [{"date": "2026-10-02", "close": 1234.0}],
    )
    client = SectorsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    history = load_index_history("3m", today=date(2026, 10, 3), client=client)
    assert history["source"] == "Yahoo Finance"
    assert history["session_date"] == "2026-10-02"
    assert history["close"] == 1234.0


def test_history_routes_reject_bad_ranges_and_unknown_symbols_without_sectors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(*args, **kwargs):
        raise AssertionError("Sectors client should not be constructed")

    monkeypatch.setattr("app.routers.market.SectorsClient", explode)
    assert api_client.get("/api/market/ihsg/history?range=1d").status_code == 400
    assert api_client.get("/api/market/ihsg/history?range=2w").status_code == 400
    assert api_client.get("/api/market/history/NOPE").status_code == 404
    assert api_client.get("/api/market/history/BB").status_code == 400


def _index_rows(start: str, end: str) -> list[dict]:
    rows = []
    for session_date, price in _weekday_prices(start, end):
        rows.append({"index_code": "IHSG", "date": session_date, "price": price})
    return rows


def _stock_rows(start: str, end: str) -> list[dict]:
    rows = []
    for session_date, price in _weekday_prices(start, end):
        rows.append(
            {
                "symbol": "BBCA.JK",
                "date": session_date,
                "close": price,
                "open": price,
                "high": price,
                "low": price,
                "volume": 1,
                "market_cap": 1,
            }
        )
    return rows


def _weekday_prices(start: str, end: str) -> list[tuple[str, float]]:
    day = date.fromisoformat(start)
    stop = date.fromisoformat(end)
    rows = []
    price = 1000.0
    while day <= stop:
        if day.weekday() < 5:
            rows.append((day.isoformat(), price))
            price += 1
        day += timedelta(days=1)
    return rows


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
            "2026-09-21T00:00:00+00:00",
        ),
    )
