import httpx
import pytest

from app.config import settings
from app.sectors.client import SectorsClient, SectorsClientError
from app.sectors.credits import credits_used
from app.sectors.paths import COMPANIES_SCREENER_PATH, FOREIGN_FLOW_PATH
from app.sectors.snapshot import run_snapshot


def _pagination(*, total_count: int, page_size: int, page_offset: int) -> dict:
    shown_count = min(page_size, max(total_count - page_offset, 0))
    has_next_page = page_offset + shown_count < total_count
    return {
        "total_count": total_count,
        "showing": shown_count,
        "limit": page_size,
        "offset": page_offset,
        "has_next": has_next_page,
        "has_previous": page_offset > 0,
        "next_offset": page_offset + page_size if has_next_page else None,
        "previous_offset": None if page_offset == 0 else max(page_offset - page_size, 0),
    }


def test_natural_language_query_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")
    client = SectorsClient(http_client=httpx.Client())
    with pytest.raises(SectorsClientError, match="Natural-language"):
        client.get(
            COMPANIES_SCREENER_PATH,
            {"q": "top banks"},
            success_credit_cost=1,
        )


def test_cache_hit_does_not_charge_credits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")
    live_calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        live_calls["count"] += 1
        assert request.headers.get("Authorization") == "test-key-not-real"
        return httpx.Response(
            200,
            json={
                "results": [{"symbol": "BBCA.JK", "company_name": "PT Bank Central Asia Tbk."}],
                "pagination": _pagination(total_count=1, page_size=200, page_offset=0),
            },
        )

    client = SectorsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    first = client.get(COMPANIES_SCREENER_PATH, {"limit": 200}, success_credit_cost=1)
    second = client.get(COMPANIES_SCREENER_PATH, {"limit": 200}, success_credit_cost=1)
    assert first.cache_hit is False
    assert first.credits_charged == 1
    assert second.cache_hit is True
    assert second.credits_charged == 0
    assert live_calls["count"] == 1
    assert credits_used() == 1


def test_structured_400_is_free(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": "INVALID_WHERE_CLAUSE", "message": "bad field"},
        )

    client = SectorsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    response = client.get(
        COMPANIES_SCREENER_PATH,
        {"where": "not_a_real_field IS NULL"},
        success_credit_cost=1,
    )
    assert response.status_code == 400
    assert response.credits_charged == 0
    assert credits_used() == 0


def test_retries_on_429_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(
                429,
                json={"error": "RATE_LIMIT_EXCEEDED"},
                headers={"Retry-After": "0"},
            )
        return httpx.Response(
            200,
            json={"results": [], "pagination": _pagination(total_count=0, page_size=30, page_offset=0)},
        )

    client = SectorsClient(http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    response = client.get(FOREIGN_FLOW_PATH, {"limit": 30}, success_credit_cost=1)
    assert response.status_code == 200
    assert attempts["count"] == 2
    assert response.credits_charged == 1


def test_snapshot_materializes_cached_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sectors_api_key", "test-key-not-real")

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/v2/companies/" in url:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "symbol": "BBCA.JK",
                            "company_name": "PT Bank Central Asia Tbk.",
                            "query_values": {
                                "market_cap": 753611199412500,
                                "last_close_price": 6175,
                                "sector": "Financials",
                            },
                        }
                    ],
                    "pagination": _pagination(total_count=1, page_size=200, page_offset=0),
                },
            )
        if "/v2/foreign-flow/" in url:
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "symbol": "BBCA.JK",
                            "date": "2026-09-18",
                            "net_foreign_inflow": 1000,
                            "foreign_buy_idr": 5000,
                            "foreign_sell_idr": 4000,
                        }
                    ],
                    "pagination": _pagination(total_count=1, page_size=30, page_offset=0),
                },
            )
        return httpx.Response(404, json={"error": "not found"})

    monkeypatch.setattr(
        "app.sectors.snapshot.SectorsClient",
        lambda **kwargs: SectorsClient(
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
            **kwargs,
        ),
    )
    counts = run_snapshot(max_credits=10)
    assert counts["companies"] == 1
    assert counts["foreign_flow"] == 1
    assert counts["credits_used"] == 2

    from app.models.common import ViewTab
    from app.sectors.repository import list_screener_page

    screener_page = list_screener_page(
        sort_by="-market_capitalization",
        page_size=20,
        page_offset=0,
        view_tab=ViewTab.overview,
    )
    assert screener_page.pagination.total_count == 1
    assert screener_page.results[0].ticker_symbol == "BBCA.JK"
    assert screener_page.results[0].market_capitalization == 753611199412500
    assert screener_page.results[0].net_foreign_inflow == 1000
    assert screener_page.results[0].score.overall_score is None or 0 <= screener_page.results[0].score.overall_score <= 100
