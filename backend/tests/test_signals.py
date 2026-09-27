from fastapi.testclient import TestClient
import httpx
import pytest

from app.config import settings
from app.main import app
from app.models.common import SignalKind, ViewTab
from app.sectors.client import SectorsClient
from app.sectors.credits import credits_used
from app.sectors.database import get_database
from app.sectors.repository import list_screener_page
from app.sectors.signals_snapshot import run_signals_snapshot
from app.services.signals import badges_for_stock


def test_mover_and_foreign_accumulation_from_cache() -> None:
    badges = badges_for_stock(
        symbol="MOVE.JK",
        daily_close_change=0.08,
        last_close_price=1000,
        is_sectors_52w_high=False,
        high_52w=None,
        net_foreign_inflow=6_000_000_000,
        foreign_buy_value=18_000_000_000,
        foreign_sell_value=12_000_000_000,
        insider_buy=None,
    )
    kinds = {badge.signal_kind for badge in badges}
    assert SignalKind.mover in kinds
    assert SignalKind.foreign_accumulation in kinds
    assert "8.0%" in next(
        badge.reason for badge in badges if badge.signal_kind == SignalKind.mover
    )


def test_52w_high_prefers_sectors_tag() -> None:
    badges = badges_for_stock(
        symbol="HIGH.JK",
        daily_close_change=0.0,
        last_close_price=90,
        is_sectors_52w_high=True,
        high_52w=200,
        net_foreign_inflow=None,
        foreign_buy_value=None,
        foreign_sell_value=None,
        insider_buy=None,
    )
    assert badges[0].signal_kind == SignalKind.fifty_two_week_high
    assert "52-w-high" in badges[0].reason


def test_52w_high_yahoo_fallback_within_tolerance() -> None:
    near = badges_for_stock(
        symbol="NEAR.JK",
        daily_close_change=0.0,
        last_close_price=100,
        is_sectors_52w_high=False,
        high_52w=101,
        net_foreign_inflow=None,
        foreign_buy_value=None,
        foreign_sell_value=None,
        insider_buy=None,
    )
    assert near[0].signal_kind == SignalKind.fifty_two_week_high
    assert "Yahoo" in near[0].reason
    far = badges_for_stock(
        symbol="FAR.JK",
        daily_close_change=0.0,
        last_close_price=90,
        is_sectors_52w_high=False,
        high_52w=1200,
        net_foreign_inflow=None,
        foreign_buy_value=None,
        foreign_sell_value=None,
        insider_buy=None,
    )
    assert far == []


def test_insider_buying_and_missing_data() -> None:
    badges = badges_for_stock(
        symbol="INSD.JK",
        daily_close_change=0.01,
        last_close_price=1000,
        is_sectors_52w_high=False,
        high_52w=1200,
        net_foreign_inflow=100,
        foreign_buy_value=100,
        foreign_sell_value=50,
        insider_buy={
            "holder_name": "Jane Doe",
            "filed_at": "2026-09-18T10:00:00",
            "amount_transaction": 1000.0,
        },
    )
    kinds = {badge.signal_kind for badge in badges}
    assert SignalKind.insider_buying in kinds
    assert "1,000 shares" in next(
        badge.reason for badge in badges if badge.signal_kind == SignalKind.insider_buying
    )
    assert SignalKind.mover not in kinds
    assert SignalKind.fifty_two_week_high not in kinds
    empty = badges_for_stock(
        symbol="NONE.JK",
        daily_close_change=None,
        last_close_price=None,
        is_sectors_52w_high=False,
        high_52w=None,
        net_foreign_inflow=None,
        foreign_buy_value=None,
        foreign_sell_value=None,
        insider_buy=None,
    )
    assert empty == []


def test_screener_attaches_signals_and_filter() -> None:
    database = get_database()
    database.execute(
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
            "MOVE.JK",
            "Synthetic Mover",
            "Industrials",
            "Industrial Goods",
            "Main",
            1000,
            0.12,
            200_000_000_000,
            1,
            10,
            1,
            1,
            0.2,
            0,
            "{}",
            "2026-09-21T00:00:00+00:00",
        ),
    )
    database.execute(
        """
        INSERT INTO fifty_two_week_high_flags (ticker_symbol, last_close_price, fetched_at)
        VALUES (?, ?, ?)
        """,
        ("MOVE.JK", 1000, "2026-09-21T00:00:00+00:00"),
    )
    database.execute(
        """
        INSERT INTO insider_filings (
            ticker_symbol, filed_at, holder_name, holder_type, transaction_type,
            amount_transaction, transaction_value, title, source_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "MOVE.JK",
            "2026-09-18T00:00:00",
            "Jane Doe",
            "insider",
            "buy",
            5000,
            5_000_000,
            "Jane Doe buys MOVE",
            "https://example.invalid/filing",
        ),
    )
    page = list_screener_page(
        sort_by="-daily_close_change",
        page_size=20,
        page_offset=0,
        view_tab=ViewTab.overview,
    )
    assert page.pagination.total_count == 1
    kinds = {badge.signal_kind.value for badge in page.results[0].signals}
    assert "mover" in kinds
    assert "fifty_two_week_high" in kinds
    assert "insider_buying" in kinds
    filtered = list_screener_page(
        sort_by="-daily_close_change",
        page_size=20,
        page_offset=0,
        view_tab=ViewTab.overview,
        signal_filter="mover",
    )
    assert filtered.pagination.total_count == 1
    empty = list_screener_page(
        sort_by="-daily_close_change",
        page_size=20,
        page_offset=0,
        view_tab=ViewTab.overview,
        signal_filter="foreign_accumulation",
    )
    assert empty.pagination.total_count == 0

    api_client = TestClient(app)
    response = api_client.get("/api/screener?signal_filter=mover")
    assert response.status_code == 200
    assert response.json()["pagination"]["total_count"] == 1
    invalid = api_client.get("/api/screener?signal_filter=not_a_signal")
    assert invalid.status_code == 422
    stock = api_client.get("/api/stocks/MOVE")
    assert stock.status_code == 200
    stock_kinds = {badge["signal_kind"] for badge in stock.json()["signals"]}
    assert stock_kinds == kinds


def test_derived_cache_rebuilds_after_insert() -> None:
    empty = list_screener_page(
        sort_by="-overall_score",
        page_size=20,
        page_offset=0,
        view_tab=ViewTab.overview,
    )
    assert empty.pagination.total_count == 0
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
            "NEW1.JK",
            "New Name",
            "Industrials",
            "Industrial Goods",
            "Main",
            1000,
            0.0,
            200_000_000_000,
            1,
            10,
            1,
            1,
            0.2,
            0,
            "{}",
            "2026-09-21T00:00:00+00:00",
        ),
    )
    filled = list_screener_page(
        sort_by="-overall_score",
        page_size=20,
        page_offset=0,
        view_tab=ViewTab.overview,
    )
    assert filled.pagination.total_count == 1
    assert filled.results[0].ticker_symbol == "NEW1.JK"


def test_signals_snapshot_materializes_documented_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")
    live_calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        live_calls["count"] += 1
        url = str(request.url)
        if "/v2/companies/" in url:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "symbol": "HIGH.JK",
                            "company_name": "High Co",
                            "query_values": {"last_close_price": 1234},
                        }
                    ],
                    "pagination": {
                        "total_count": 1,
                        "showing": 1,
                        "limit": 200,
                        "offset": 0,
                        "has_next": False,
                        "has_previous": False,
                        "next_offset": None,
                        "previous_offset": None,
                    },
                },
            )
        if "/v2/filings/" in url:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Jane Doe buys HIGH",
                            "source": "https://example.invalid/filing",
                            "timestamp": "2026-09-18T10:00:00",
                            "symbol": "HIGH.JK",
                            "transaction_type": "buy",
                            "holder_type": "insider",
                            "holder_name": "Jane Doe",
                            "amount_transaction": 1000,
                            "transaction_value": 1_000_000,
                        }
                    ],
                    "pagination": {
                        "total_count": 1,
                        "showing": 1,
                        "limit": 30,
                        "offset": 0,
                        "has_next": False,
                        "has_previous": False,
                        "next_offset": None,
                        "previous_offset": None,
                    },
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    monkeypatch.setattr(
        "app.sectors.signals_snapshot.SectorsClient",
        lambda **kwargs: SectorsClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            **kwargs,
        ),
    )
    counts = run_signals_snapshot(max_credits=8)
    assert counts["fifty_two_week_high"] == 1
    assert counts["insider_filings"] == 1
    assert counts["credits_used"] == 2
    first_live_calls = live_calls["count"]
    cached = run_signals_snapshot(max_credits=8)
    assert cached["credits_used"] == 0
    assert live_calls["count"] == first_live_calls
    assert credits_used() == 2
    flags = get_database().execute(
        "SELECT ticker_symbol FROM fifty_two_week_high_flags"
    ).fetchall()
    assert [row["ticker_symbol"] for row in flags] == ["HIGH.JK"]
    filings = get_database().execute(
        "SELECT holder_name, amount_transaction FROM insider_filings"
    ).fetchone()
    assert filings["holder_name"] == "Jane Doe"
    assert filings["amount_transaction"] == 1000
