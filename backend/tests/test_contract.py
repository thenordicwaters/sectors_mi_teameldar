from fastapi.testclient import TestClient

from app.main import app
from app.models.common import ScoreBreakdown
from app.models.screener import ScreenerRow

api_client = TestClient(app)


def test_health() -> None:
    response = api_client.get("/health")
    assert response.status_code == 200
    assert "Not investment advice" in response.json()["disclaimer"]


def test_screener_stub_is_empty() -> None:
    response = api_client.get("/api/screener")
    response_body = response.json()
    assert response.status_code == 200
    assert response_body["results"] == []
    assert response_body["pagination"]["total_count"] == 0


def test_compare_requires_two_symbols() -> None:
    assert api_client.get("/api/compare?ticker_symbols=BBCA").status_code == 400
    response_body = api_client.get(
        "/api/compare?ticker_symbols=BBCA,BMRI"
    ).json()
    assert response_body["ticker_symbols"] == ["BBCA.JK", "BMRI.JK"]


def test_screener_row_requires_score() -> None:
    screener_row = ScreenerRow(
        ticker_symbol="BBCA.JK",
        company_name="PT Bank Central Asia Tbk.",
        score=ScoreBreakdown(
            overall_score=0,
            value_score=0,
            quality_score=0,
            momentum_score=0,
            flow_score=0,
        ),
    )
    assert screener_row.has_anomaly is False
    assert screener_row.signals == []
