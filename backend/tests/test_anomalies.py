from fastapi.testclient import TestClient

from app.main import app
from app.models.anomalies import AnomalyKind
from app.sectors.database import get_database
from app.sectors.repository import list_screener_page, list_unusual_activity_page
from app.models.common import ViewTab
from app.services.anomalies import (
    MIN_FOREIGN_FLOW_CROSS_SECTION,
    AnomalyInput,
    detect_unusual_activity,
)


def _volume_stock(symbol: str, volume: float) -> AnomalyInput:
    return AnomalyInput(
        symbol=symbol,
        company_name=f"{symbol} Co",
        volume=volume,
        volume_average=1_000_000,
        volume_standard_deviation=100_000,
        volume_baseline_sessions=60,
        volume_as_of_date="2026-09-21",
    )


def test_volume_standard_score_flags_spike_with_reason() -> None:
    flags = detect_unusual_activity([_volume_stock("SPKE.JK", 1_500_000)])
    flag = flags["SPKE.JK"][0]
    assert flag.anomaly_kind == AnomalyKind.volume_standard_score
    assert flag.standard_score == 5.0
    assert flag.label == "Volume spike"
    assert "5.0 standard deviations above its 60-session average" in flag.reason
    assert "1.5x normal" in flag.reason
    assert "2026-09-21" in flag.reason


def test_volume_standard_score_respects_threshold_and_gates() -> None:
    assert detect_unusual_activity([_volume_stock("CALM.JK", 1_200_000)]) == {}
    short_history = _volume_stock("NEWL.JK", 2_000_000)
    short_history.volume_baseline_sessions = 10
    assert detect_unusual_activity([short_history]) == {}
    flat = _volume_stock("FLAT.JK", 2_000_000)
    flat.volume_standard_deviation = 0
    assert detect_unusual_activity([flat]) == {}
    missing = AnomalyInput(symbol="NONE.JK", company_name="No Data Co")
    assert detect_unusual_activity([missing]) == {}


def _flow_stock(symbol: str, net: float, average_traded_value: float) -> AnomalyInput:
    return AnomalyInput(
        symbol=symbol,
        company_name=f"{symbol} Co",
        average_traded_value=average_traded_value,
        net_foreign_inflow=net,
        flow_as_of_date="2026-09-18",
    )


def _balanced_cross_section() -> list[AnomalyInput]:
    """Enough ordinary tickers for a median and a median absolute deviation."""
    stocks = []
    for index in range(MIN_FOREIGN_FLOW_CROSS_SECTION):
        ordinary_multiple = (index % 7 - 3) / 100
        stocks.append(
            _flow_stock(
                f"F{index:03d}.JK",
                10_000_000_000 * ordinary_multiple,
                10_000_000_000,
            )
        )
    return stocks


def test_foreign_flow_standard_score_is_cross_sectional() -> None:
    universe = _balanced_cross_section()
    universe.append(_flow_stock("BUYY.JK", 30_000_000_000, 10_000_000_000))
    flags = detect_unusual_activity(universe)
    flag = flags["BUYY.JK"][0]
    assert flag.anomaly_kind == AnomalyKind.foreign_flow_standard_score
    assert flag.standard_score > 8
    assert flag.label == "Foreign inflow spike"
    assert "net buyers of Rp 30.0B" in flag.reason
    assert "3.0x this stock's 20-session average traded value" in flag.reason
    assert "robust standard deviations above the IDX median" in flag.reason
    assert "2026-09-18" in flag.reason
    assert not any(symbol.startswith("F0") for symbol in flags)


def test_foreign_flow_gates_on_size_and_sample() -> None:
    universe = _balanced_cross_section()
    # Many times its normal turnover, but the net value is under the Rp 1 billion floor.
    universe.append(_flow_stock("TINY.JK", 900_000_000, 100_000_000))
    # Large and one-sided, but normal turnover is under the Rp 100 million floor.
    universe.append(_flow_stock("THIN.JK", 5_000_000_000, 50_000_000))
    flags = detect_unusual_activity(universe)
    assert "TINY.JK" not in flags
    assert "THIN.JK" not in flags
    small_cross_section = [_flow_stock("ONEE.JK", 30_000_000_000, 10_000_000_000)]
    assert detect_unusual_activity(small_cross_section) == {}


def test_foreign_flow_needs_a_cross_section_with_spread() -> None:
    """Identical tickers give a zero deviation: nothing to measure against, no flags."""
    universe = [
        _flow_stock(f"S{index:03d}.JK", 1_000_000_000, 10_000_000_000)
        for index in range(MIN_FOREIGN_FLOW_CROSS_SECTION)
    ]
    universe.append(_flow_stock("OUTL.JK", 30_000_000_000, 10_000_000_000))
    assert detect_unusual_activity(universe) == {}


def _insert_company(symbol: str, name: str) -> None:
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
            name,
            "Industrials",
            "Industrial Goods",
            "Main",
            1000,
            0.01,
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


def test_unusual_activity_endpoint_serves_flags_from_the_cache() -> None:
    _insert_company("SPKE.JK", "Volume Spike Co")
    get_database().execute(
        """
        INSERT INTO yahoo_price_overlay (
            ticker_symbol, volume, volume_average, volume_standard_deviation,
            volume_baseline_sessions, as_of_date, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "SPKE.JK",
            8_000_000,
            1_000_000,
            500_000,
            60,
            "2026-09-21",
            "2026-09-21T00:00:00+00:00",
        ),
    )

    page = list_unusual_activity_page(
        anomaly_kind=None,
        min_standard_score=3.0,
        page_size=20,
        page_offset=0,
    )
    assert page.pagination.total_count == 1
    assert page.results[0].ticker_symbol == "SPKE.JK"
    assert page.results[0].standard_score == 14.0
    assert page.method_notes

    screener = list_screener_page(
        sort_by="-overall_score",
        page_size=20,
        page_offset=0,
        view_tab=ViewTab.overview,
    )
    assert screener.results[0].has_anomaly is True
    assert screener.results[0].anomalies[0].anomaly_kind == (
        AnomalyKind.volume_standard_score
    )

    api_client = TestClient(app)
    response = api_client.get("/api/unusual")
    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total_count"] == 1
    assert "Not investment advice" in body["disclaimer"]
    assert (
        api_client.get(
            "/api/unusual?anomaly_kind=foreign_flow_standard_score"
        ).json()["pagination"]["total_count"]
        == 0
    )
    assert api_client.get("/api/unusual?min_standard_score=20").json()[
        "pagination"
    ]["total_count"] == 0
    assert api_client.get("/api/unusual?min_standard_score=1").status_code == 422
    assert api_client.get("/api/unusual?anomaly_kind=not_a_kind").status_code == 422
    assert (
        api_client.get("/api/screener?anomaly_only=true").json()["pagination"][
            "total_count"
        ]
        == 1
    )
    assert api_client.get("/api/stocks/SPKE").json()["has_anomaly"] is True


def test_unusual_activity_is_empty_without_volume_or_flow_data() -> None:
    _insert_company("QUIT.JK", "Quiet Co")
    page = list_unusual_activity_page(
        anomaly_kind=None,
        min_standard_score=3.0,
        page_size=20,
        page_offset=0,
    )
    assert page.results == []
    assert page.pagination.total_count == 0
