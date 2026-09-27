import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.sectors.client import SectorsClient
from app.sectors.credits import credits_used
from app.sectors.database import get_database
from app.sectors.where_clause import (
    EXAMPLE_CLAUSES,
    MAX_CLAUSE_LENGTH,
    WhereClauseError,
    validate_order_by,
    validate_where_clause,
)


def test_documented_clauses_validate() -> None:
    for clause in EXAMPLE_CLAUSES:
        assert validate_where_clause(clause).clause == clause
    assert validate_where_clause("company_name like '%energi%'").fields == ("company_name",)
    assert validate_where_clause(
        "sector = 'Financials' and listing_date > '2005-01-01'"
    ).condition_count == 2
    assert validate_where_clause("revenue_q[Q1-2024] > 1000000000").fields == (
        "revenue_q[Q1-2024]",
    )
    assert validate_where_clause("last_close_price < 52_w_high_price * 0.8").fields == (
        "last_close_price",
        "52_w_high_price",
    )
    assert validate_where_clause("  market_cap   >   1000  ").clause == "market_cap > 1000"


def test_unknown_field_is_rejected_with_a_suggestion() -> None:
    with pytest.raises(WhereClauseError) as error:
        validate_where_clause("market_capp > 1000")
    assert "not a Sectors screener field" in error.value.message
    assert "market_cap" in error.value.suggestions


def test_yearly_and_quarterly_fields_need_bracket_notation() -> None:
    with pytest.raises(WhereClauseError, match=r"revenue\[2024\]"):
        validate_where_clause("revenue > 1000")
    with pytest.raises(WhereClauseError, match=r"four-digit year"):
        validate_where_clause("revenue[24] > 1000")
    with pytest.raises(WhereClauseError, match=r"outside"):
        validate_where_clause("revenue[1900] > 1000")
    with pytest.raises(WhereClauseError, match=r"Q1-2024"):
        validate_where_clause("revenue_q[2024] > 1000")
    with pytest.raises(WhereClauseError, match=r"does not take bracket notation"):
        validate_where_clause("market_cap[2024] > 1000")


def test_injection_and_shape_problems_are_rejected() -> None:
    for clause in (
        "",
        "   ",
        "market_cap > 1000; drop table company_universe",
        "market_cap > 1000 -- comment",
        "sector = 'Financials",
        "(market_cap > 1000",
        "market_cap",
        "1 = 1",
        "market_cap > 1000 and " + " and ".join(["pe_ttm < 15"] * 10),
        "market_cap > " + "9" * MAX_CLAUSE_LENGTH,
    ):
        with pytest.raises(WhereClauseError):
            validate_where_clause(clause)


def test_order_by_accepts_one_field() -> None:
    assert validate_order_by("-market_cap") == "-market_cap"
    assert validate_order_by("roe[2024]") == "roe[2024]"
    with pytest.raises(WhereClauseError):
        validate_order_by("-(earnings[2024]/earnings[2023])")
    with pytest.raises(WhereClauseError):
        validate_order_by("not_a_field")
    with pytest.raises(WhereClauseError):
        validate_order_by("")


def test_fields_endpoint_costs_nothing() -> None:
    api_client = TestClient(app)
    body = api_client.get("/api/screener/custom/fields").json()
    assert "market_cap" in body["direct_fields"]
    assert "tags" in body["array_fields"]
    assert "roe" in body["yearly_fields"]
    assert body["credits_per_page"] == 1
    assert credits_used() == 0


def test_invalid_clause_never_reaches_sectors() -> None:
    api_client = TestClient(app)
    response = api_client.get("/api/screener/custom?where=market_capp > 1000")
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["credits_charged"] == 0
    assert "market_cap" in detail["suggestions"]
    assert credits_used() == 0
    assert api_client.get("/api/screener/custom").status_code == 422


def test_dry_run_reports_cost_without_calling_sectors() -> None:
    api_client = TestClient(app)
    body = api_client.get(
        "/api/screener/custom?where=market_cap > 1000&dry_run=true"
    ).json()
    assert body["results"] == []
    assert body["credits_charged"] == 0
    assert any("Dry run" in note for note in body["notes"])
    assert credits_used() == 0


def test_cached_screener_rejects_a_where_clause() -> None:
    api_client = TestClient(app)
    response = api_client.get("/api/screener?filter_clause=market_cap > 1000")
    assert response.status_code == 400
    assert "/api/screener/custom" in response.json()["detail"]
    assert credits_used() == 0


def _mock_sectors(monkeypatch: pytest.MonkeyPatch, counter: dict) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")

    def handler(request: httpx.Request) -> httpx.Response:
        counter["count"] += 1
        counter["last_url"] = str(request.url)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "symbol": "CACH.JK",
                        "company_name": "Cached Co",
                        "query_values": {"market_cap": 200_000_000_000},
                    },
                    {
                        "symbol": "LIVE.JK",
                        "company_name": "Live Only Co",
                        "query_values": {
                            "market_cap": 150_000_000_000,
                            "last_close_price": 500,
                            "pe_ttm": 9,
                        },
                    },
                ],
                "pagination": {
                    "total_count": 2,
                    "showing": 2,
                    "limit": 50,
                    "offset": 0,
                    "has_next": False,
                    "has_previous": False,
                    "next_offset": None,
                    "previous_offset": None,
                },
            },
        )

    monkeypatch.setattr(
        "app.routers.screener.SectorsClient",
        lambda **kwargs: SectorsClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            **kwargs,
        ),
    )


def test_custom_screen_merges_cached_score_and_bills_one_credit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            "CACH.JK",
            "Cached Co",
            "Industrials",
            "Industrial Goods",
            "Main",
            1000,
            0.08,
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
    counter = {"count": 0}
    _mock_sectors(monkeypatch, counter)
    api_client = TestClient(app)

    body = api_client.get(
        "/api/screener/custom?where=market_cap > 100000000000&order_by=-market_cap"
    ).json()
    assert body["where_clause"] == "market_cap > 100000000000"
    assert body["credits_charged"] == 1
    assert body["cache_hit"] is False
    assert body["scored_from_cache"] == 1
    assert [row["ticker_symbol"] for row in body["results"]] == ["CACH.JK", "LIVE.JK"]
    assert any(badge["signal_kind"] == "mover" for badge in body["results"][0]["signals"])
    assert body["results"][1]["score"]["overall_score"] is None
    assert body["results"][1]["price_to_earnings_trailing_twelve_months"] == 9
    assert "include_query_values=true" in counter["last_url"]
    assert credits_used() == 1

    cached = api_client.get(
        "/api/screener/custom?where=market_cap > 100000000000&order_by=-market_cap"
    ).json()
    assert cached["credits_charged"] == 0
    assert cached["cache_hit"] is True
    assert counter["count"] == 1
    assert credits_used() == 1


def test_sectors_rejection_is_reported_as_free(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"message": "unsupported comparison"})

    monkeypatch.setattr(
        "app.routers.screener.SectorsClient",
        lambda **kwargs: SectorsClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            **kwargs,
        ),
    )
    response = TestClient(app).get("/api/screener/custom?where=esg_score > 1000")
    assert response.status_code == 422
    assert response.json()["detail"]["credits_charged"] == 0
    assert "unsupported comparison" in response.json()["detail"]["message"]
    assert credits_used() == 0


def test_missing_api_key_is_a_clear_error() -> None:
    api_client = TestClient(app)
    response = api_client.get("/api/screener/custom?where=market_cap > 1000")
    assert response.status_code == 503
    assert "SECTORS_API_KEY" in response.json()["detail"]
    assert credits_used() == 0
