import json

from fastapi.testclient import TestClient

from app.main import app
from app.sectors.database import get_database

api_client = TestClient(app)


def _insert_synthetic_company(*, symbol: str, sector: str, pe: float, roe: float) -> None:
    query_values = {
        "market_cap": 200_000_000_000,
        "last_close_price": 1000,
        "daily_close_change": 0.02,
        "pe_ttm": pe,
        "roe_ttm": roe,
        "sector": sector,
        "sub_sector": "Banks" if sector == "Financials" else "Industrial Goods",
        "listing_board": "Main",
    }
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
            f"Synthetic {symbol}",
            sector,
            query_values["sub_sector"],
            "Main",
            1000,
            0.02,
            200_000_000_000,
            1,
            pe,
            1.0,
            1.0,
            roe,
            0.0,
            json.dumps(query_values),
            "2026-09-21T00:00:00+00:00",
        ),
    )
    get_database().execute(
        """
        INSERT INTO foreign_flow (
            ticker_symbol, trading_date, net_foreign_inflow,
            foreign_buy_value_rupiah, foreign_sell_value_rupiah
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (symbol, "2026-09-18", 1_000_000, 4_000_000, 3_000_000),
    )


def test_scores_route_reads_cache_only() -> None:
    _insert_synthetic_company(symbol="SYN1.JK", sector="Industrials", pe=10, roe=0.2)
    _insert_synthetic_company(symbol="SYN2.JK", sector="Industrials", pe=20, roe=0.1)
    response = api_client.get("/api/scores")
    body = response.json()
    assert response.status_code == 200
    assert body["universe_size"] == 2
    assert "Not investment advice" in body["disclaimer"]
    assert body["weights"]["quality"] == 30
    symbols = {row["symbol"] for row in body["results"]}
    assert symbols == {"SYN1.JK", "SYN2.JK"}
    detail = api_client.get("/api/scores/SYN1")
    assert detail.status_code == 200
    assert detail.json()["symbol"] == "SYN1.JK"
    assert "magic_formula" in detail.json()["methods"]


def test_score_weight_override_and_missing_symbol() -> None:
    _insert_synthetic_company(symbol="SYN1.JK", sector="Industrials", pe=10, roe=0.2)
    response = api_client.get("/api/scores?quality=40&value=20&momentum=20&flow=20")
    assert response.status_code == 200
    assert response.json()["weights"]["quality"] == 40
    missing = api_client.get("/api/scores/ZZZZ")
    assert missing.status_code == 404
