from fastapi.testclient import TestClient

from app.main import app
from app.models.common import ScoreBreakdown
from app.models.screener import ScreenerRow

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert "Not investment advice" in response.json()["disclaimer"]


def test_screener_stub_is_empty() -> None:
    response = client.get("/api/screener")
    body = response.json()
    assert response.status_code == 200
    assert body["results"] == []
    assert body["pagination"]["total_count"] == 0


def test_compare_requires_two_symbols() -> None:
    assert client.get("/api/compare?symbols=BBCA").status_code == 400
    body = client.get("/api/compare?symbols=BBCA,BMRI").json()
    assert body["symbols"] == ["BBCA.JK", "BMRI.JK"]


def test_screener_row_requires_score() -> None:
    row = ScreenerRow(
        symbol="BBCA.JK",
        company_name="PT Bank Central Asia Tbk.",
        score=ScoreBreakdown(
            overall=0, value=0, quality=0, momentum=0, flow=0
        ),
    )
    assert row.anomaly is False
    assert row.signals == []
