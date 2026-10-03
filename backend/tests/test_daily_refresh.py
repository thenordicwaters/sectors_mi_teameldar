from datetime import date

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.sectors.daily_refresh import (
    DAILY_CREDIT_CAP,
    PLANNED_DAILY_CREDITS,
    SIGNALS_CREDIT_CAP,
    SNAPSHOT_CREDIT_CAP,
    RefreshSteps,
    join_daily_refresh,
    run_daily_refresh,
    schedule_daily_refresh,
)
from app.sectors.database import get_database


def test_planned_daily_cost_stays_under_100_credits() -> None:
    assert PLANNED_DAILY_CREDITS == 33
    assert DAILY_CREDIT_CAP < 100
    assert SNAPSHOT_CREDIT_CAP + SIGNALS_CREDIT_CAP <= DAILY_CREDIT_CAP


def test_first_request_of_the_day_starts_one_refresh(monkeypatch) -> None:
    monkeypatch.setattr(settings, "daily_refresh_enabled", True)
    started: list[str] = []

    def fake_run(day: str) -> None:
        started.append(day)

    monkeypatch.setattr("app.sectors.daily_refresh._safe_run", fake_run)
    assert schedule_daily_refresh(date(2026, 10, 3)) is True
    join_daily_refresh()
    assert started == ["2026-10-03"]
    assert schedule_daily_refresh(date(2026, 10, 3)) is False
    row = get_database().execute(
        "SELECT status FROM daily_refresh WHERE refresh_date = '2026-10-03'"
    ).fetchone()
    assert row["status"] == "running"


def test_refresh_runs_snapshot_signals_ihsg_and_yahoo() -> None:
    calls: list[tuple] = []

    class Steps(RefreshSteps):
        def snapshot(self, *, force_refresh: bool, max_credits: int) -> dict:
            calls.append(("snapshot", force_refresh, max_credits))
            return {"companies": 2, "foreign_flow": 2, "credits_used": 8}

        def signals(self, *, force_refresh: bool, max_credits: int) -> dict:
            calls.append(("signals", force_refresh, max_credits))
            return {"fifty_two_week_high": 1, "insider_filings": 1, "credits_used": 2}

        def ihsg(self, *, max_credits: int) -> dict:
            calls.append(("ihsg", max_credits))
            return {"history_session": "2026-10-02"}

        def yahoo(self) -> int:
            calls.append(("yahoo",))
            return 2

        def credits_used(self) -> int:
            return 0

    _ensure_claim("2026-10-03")
    detail = run_daily_refresh("2026-10-03", steps=Steps())
    assert calls == [
        ("snapshot", True, SNAPSHOT_CREDIT_CAP),
        ("signals", True, SIGNALS_CREDIT_CAP),
        ("ihsg", DAILY_CREDIT_CAP),
        ("yahoo",),
    ]
    assert detail["scores"] == "recomputed from the refreshed cache"
    row = get_database().execute(
        "SELECT status, credits_used FROM daily_refresh WHERE refresh_date = '2026-10-03'"
    ).fetchone()
    assert row["status"] == "complete"


def test_credit_cap_skips_later_sectors_steps() -> None:
    calls: list[str] = []

    class Steps(RefreshSteps):
        def snapshot(self, *, force_refresh: bool, max_credits: int) -> dict:
            calls.append("snapshot")
            return {}

        def signals(self, *, force_refresh: bool, max_credits: int) -> dict:
            calls.append("signals")
            return {}

        def ihsg(self, *, max_credits: int) -> dict:
            calls.append("ihsg")
            return {}

        def yahoo(self) -> int:
            calls.append("yahoo")
            return 0

        def credits_used(self) -> int:
            return DAILY_CREDIT_CAP if calls else 0

    _ensure_claim("2026-10-04")
    detail = run_daily_refresh("2026-10-04", steps=Steps())
    assert calls == ["snapshot", "yahoo"]
    assert detail["signals"] == "skipped: credit cap"
    assert detail["ihsg"] == "skipped: credit cap"


def test_zero_credit_failure_releases_the_day_for_a_later_retry(monkeypatch) -> None:
    monkeypatch.setattr(settings, "daily_refresh_enabled", True)

    class Steps(RefreshSteps):
        def snapshot(self, *, force_refresh: bool, max_credits: int) -> dict:
            raise RuntimeError("sectors unavailable")

        def credits_used(self) -> int:
            return 0

    _ensure_claim("2026-10-05")
    detail = run_daily_refresh("2026-10-05", steps=Steps())
    assert "sectors unavailable" in detail["snapshot_error"]
    assert not _claimed("2026-10-05")
    assert schedule_daily_refresh(date(2026, 10, 5)) is False


def test_spent_failure_does_not_run_again_the_same_day(monkeypatch) -> None:
    monkeypatch.setattr(settings, "daily_refresh_enabled", True)
    calls: list[str] = []

    class Steps(RefreshSteps):
        def snapshot(self, *, force_refresh: bool, max_credits: int) -> dict:
            calls.append("snapshot")
            return {}

        def signals(self, *, force_refresh: bool, max_credits: int) -> dict:
            calls.append("signals")
            raise RuntimeError("filings failed")

        def credits_used(self) -> int:
            return 5 if "snapshot" in calls else 0

    _ensure_claim("2026-10-06")
    detail = run_daily_refresh("2026-10-06", steps=Steps())
    assert detail["signals_error"] == "filings failed"
    assert "yahoo" not in calls
    row = get_database().execute(
        "SELECT status, credits_used FROM daily_refresh WHERE refresh_date = '2026-10-06'"
    ).fetchone()
    assert row["status"] == "failed"
    assert row["credits_used"] == 5
    assert schedule_daily_refresh(date(2026, 10, 6)) is False


def test_api_request_schedules_refresh_and_health_does_not(monkeypatch) -> None:
    monkeypatch.setattr(settings, "daily_refresh_enabled", True)
    scheduled: list[str] = []
    monkeypatch.setattr(
        "app.main.schedule_daily_refresh",
        lambda: scheduled.append("go") or False,
    )
    client = TestClient(app)
    client.get("/health")
    assert scheduled == []
    client.get("/api/credits")
    assert scheduled == ["go"]


def _claimed(day: str) -> bool:
    row = get_database().execute(
        "SELECT refresh_date FROM daily_refresh WHERE refresh_date = ?",
        (day,),
    ).fetchone()
    return row is not None


def _ensure_claim(day: str) -> None:
    get_database().execute(
        """
        INSERT OR IGNORE INTO daily_refresh (refresh_date, status, started_at)
        VALUES (?, 'running', '2026-10-03T00:00:00+00:00')
        """,
        (day,),
    )
