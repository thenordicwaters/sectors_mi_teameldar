import pytest

from app.config import settings
from app.sectors.daily_refresh import reset_daily_refresh_state
from app.sectors.database import reset_database


@pytest.fixture(autouse=True)
def isolated_sqlite(tmp_path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "sectors.db"
    monkeypatch.setattr(settings, "sectors_sqlite_path", str(database_path))
    monkeypatch.setattr(settings, "sectors_min_interval_seconds", 0)
    monkeypatch.setattr(settings, "sectors_opening_credits_used", 0)
    # No real key during tests: a live call must fail loudly instead of spending credits.
    monkeypatch.setattr(settings, "sectors_api_key", "")
    # Opening the test client must not start a Sectors refresh.
    monkeypatch.setattr(settings, "daily_refresh_enabled", False)
    reset_daily_refresh_state()
    reset_database()
    yield
    reset_daily_refresh_state()
    reset_database()
