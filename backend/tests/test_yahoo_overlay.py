import pandas as pd

from app.enrichment.yahoo import apply_yahoo_overlay, metrics_from_history
from app.sectors.database import get_database
from app.services.scoring.adapters.sectors import row_to_stock_inputs
from app.services.scoring.methods.momentum import MomentumMethod
from app.services.scoring.types import StockInputs


def test_yahoo_metrics_from_synthetic_history() -> None:
    dates = pd.bdate_range("2025-08-01", periods=260)
    close = pd.Series(range(100, 360), index=dates, dtype=float)
    volume = pd.Series(1_000_000, index=dates, dtype=float)
    high = pd.Series(range(110, 370), index=dates, dtype=float)
    frame = pd.DataFrame({"Close": close, "High": high, "Volume": volume})
    metrics = metrics_from_history(frame, "SYN1.JK")
    assert metrics is not None
    assert metrics["trading_days"] == 260
    assert metrics["return_1m"] is not None
    assert metrics["return_12m"] is not None
    assert metrics["high_52w"] == float(high.tail(252).max())
    assert metrics["average_traded_value"] == 1_000_000 * close.tail(20).mean()


def test_yahoo_overlay_does_not_overwrite_sectors() -> None:
    stock = StockInputs(symbol="SYN1.JK", return_1m=0.05, volume=None)
    apply_yahoo_overlay(
        stock,
        {"return_1m": 0.99, "volume": 123, "return_12m": 0.20, "average_traded_value": 50},
    )
    assert stock.return_1m == 0.05
    assert stock.volume == 123
    assert stock.return_12m == 0.20


def test_cached_yahoo_overlay_feeds_twelve_minus_one() -> None:
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
            "SYN1.JK",
            "Synthetic One",
            "Industrials",
            "Industrial Goods",
            "Main",
            1000,
            0.50,
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
        INSERT INTO yahoo_price_overlay (
            ticker_symbol, return_1m, return_12m, volume, average_traded_value,
            trading_days, last_close, as_of_date, notes, fetched_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "SYN1.JK",
            0.10,
            0.21,
            1_000_000,
            1_000_000_000,
            260,
            1000,
            "2026-09-21",
            None,
            "2026-09-21T00:00:00+00:00",
        ),
    )
    stock = row_to_stock_inputs(
        dict(
            get_database()
            .execute("SELECT * FROM company_universe WHERE ticker_symbol='SYN1.JK'")
            .fetchone()
        ),
        overlay=dict(
            get_database()
            .execute("SELECT * FROM yahoo_price_overlay WHERE ticker_symbol='SYN1.JK'")
            .fetchone()
        ),
    )
    peer = StockInputs(symbol="SYN2.JK", return_12m=0.0, return_1m=0.0)
    result = MomentumMethod().score(stock, [stock, peer])
    assert result.breakdown["source"] == "twelve_minus_one"
    assert abs(result.breakdown["twelve_minus_one"] - 0.1) < 1e-9
    assert stock.daily_return == 0.50
