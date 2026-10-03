"""Refresh cached market data once per Jakarta day, on the first API request.

Planned Sectors cost when the HTTP cache is bypassed, from the September ledger:

- company universe (prices, market cap, valuation): 5 credits
- foreign flow: 23 credits
- 52-week-high tag: 1 credit
- insider filings: 3 credits
- IHSG latest 90-day window: 1 credit

That is 33 credits. Yahoo overlay and the score methods (Piotroski, magic formula,
momentum, foreign flow, financial quality) read the refreshed cache and cost 0.
Per-symbol ``/v2/daily/{symbol}/`` is not called: one credit times the universe
is several hundred credits.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import date

from app.config import settings
from app.sectors.credits import credits_used, utc_now_iso
from app.sectors.database import get_database
from app.services.market_quotes import jakarta_today

logger = logging.getLogger("sectors.daily_refresh")

# Headroom above the 33-credit plan. Still far under a 100-credit day.
DAILY_CREDIT_CAP = 45
SNAPSHOT_CREDIT_CAP = 36
SIGNALS_CREDIT_CAP = 8
PLANNED_DAILY_CREDITS = 33
RETRY_BACKOFF_SECONDS = 15 * 60

_lock = threading.Lock()
_worker: threading.Thread | None = None
_backoff_until = 0.0


def reset_daily_refresh_state() -> None:
    global _worker, _backoff_until
    with _lock:
        worker = _worker
        _worker = None
        _backoff_until = 0.0
    if worker is not None and worker.is_alive() and worker is not threading.current_thread():
        worker.join(timeout=0.1)


def join_daily_refresh(timeout: float = 5) -> None:
    with _lock:
        worker = _worker
    if worker is not None:
        worker.join(timeout)


def schedule_daily_refresh(today: date | None = None) -> bool:
    """Claim this Jakarta date and start the refresh. False when it should not run."""
    if not settings.daily_refresh_enabled:
        return False
    if time.monotonic() < _backoff_until:
        return False
    day = (today or jakarta_today()).isoformat()
    with _lock:
        global _worker
        if _worker is not None and _worker.is_alive():
            return False
        if _already_claimed(day):
            return False
        if not _claim(day):
            return False
        _worker = threading.Thread(
            target=_safe_run,
            args=(day,),
            name="daily-refresh",
            daemon=True,
        )
        _worker.start()
        return True


def run_daily_refresh(day: str, *, steps: RefreshSteps | None = None) -> dict:
    """Run the claimed day's refresh. Does not claim the day itself."""
    steps = steps or RefreshSteps()
    before = steps.credits_used()
    detail: dict = {}
    logger.info(
        "daily refresh %s started; planned %s Sectors credits, cap %s",
        day,
        PLANNED_DAILY_CREDITS,
        DAILY_CREDIT_CAP,
    )
    try:
        detail["snapshot"] = steps.snapshot(
            force_refresh=True,
            max_credits=SNAPSHOT_CREDIT_CAP,
        )
    except Exception as error:
        return _fail(day, before, detail, "snapshot_error", error, steps)

    if _remaining(before, steps) <= 0:
        detail["signals"] = "skipped: credit cap"
        detail["ihsg"] = "skipped: credit cap"
    else:
        try:
            detail["signals"] = steps.signals(
                force_refresh=True,
                max_credits=min(SIGNALS_CREDIT_CAP, _remaining(before, steps)),
            )
        except Exception as error:
            return _fail(day, before, detail, "signals_error", error, steps)
        if _remaining(before, steps) < 1:
            detail["ihsg"] = "skipped: credit cap"
        else:
            try:
                detail["ihsg"] = steps.ihsg(max_credits=_remaining(before, steps))
            except Exception as error:
                detail["ihsg_error"] = str(error)
                logger.exception("daily refresh %s IHSG step failed", day)

    try:
        detail["yahoo"] = steps.yahoo()
    except Exception as error:
        detail["yahoo_error"] = str(error)
        logger.exception("daily refresh %s Yahoo step failed", day)

    detail["scores"] = "recomputed from the refreshed cache"
    _finish(day, "complete", steps.credits_used() - before, detail)
    logger.info(
        "daily refresh %s complete credits=%s",
        day,
        steps.credits_used() - before,
    )
    return detail


class RefreshSteps:
    """Seams for tests. Defaults are the live snapshot, signals, IHSG, and Yahoo jobs."""

    def snapshot(self, *, force_refresh: bool, max_credits: int) -> dict:
        from app.sectors.snapshot import run_snapshot

        return run_snapshot(force_refresh=force_refresh, max_credits=max_credits)

    def signals(self, *, force_refresh: bool, max_credits: int) -> dict:
        from app.sectors.signals_snapshot import run_signals_snapshot

        return run_signals_snapshot(force_refresh=force_refresh, max_credits=max_credits)

    def ihsg(self, *, max_credits: int) -> dict:
        from app.sectors.client import SectorsClient
        from app.services.market_quotes import load_ihsg_session
        from app.services.price_history import load_index_history

        client = SectorsClient(max_credits_this_run=max_credits)
        try:
            history = load_index_history("3m", client=client)
        finally:
            client.close()
        quote_session = None
        try:
            quote_session = load_ihsg_session().get("session_date")
        except Exception:
            logger.exception("yahoo IHSG session refresh failed")
        return {
            "history_session": history.get("session_date"),
            "quote_session": quote_session,
        }

    def yahoo(self) -> int:
        from app.enrichment.yahoo import enrich_symbols

        symbols = [
            row["ticker_symbol"]
            for row in get_database()
            .execute("SELECT ticker_symbol FROM company_universe ORDER BY ticker_symbol")
            .fetchall()
        ]
        return enrich_symbols(symbols, force=True)

    def credits_used(self) -> int:
        return credits_used()


def _safe_run(day: str) -> None:
    try:
        run_daily_refresh(day)
    except Exception:
        logger.exception("daily refresh %s failed", day)


def _fail(
    day: str,
    before: int,
    detail: dict,
    key: str,
    error: Exception,
    steps: RefreshSteps,
) -> dict:
    detail[key] = str(error)
    spent = steps.credits_used() - before
    if spent == 0:
        _release(day)
        _schedule_backoff()
        logger.exception("daily refresh %s spent 0 credits and will retry: %s", day, key)
        return detail
    _finish(day, "failed", spent, detail)
    logger.exception("daily refresh %s failed after %s credits: %s", day, spent, key)
    return detail


def _schedule_backoff() -> None:
    global _backoff_until
    _backoff_until = time.monotonic() + RETRY_BACKOFF_SECONDS


def _remaining(before: int, steps: RefreshSteps) -> int:
    return max(DAILY_CREDIT_CAP - (steps.credits_used() - before), 0)


def _already_claimed(day: str) -> bool:
    row = get_database().execute(
        "SELECT refresh_date FROM daily_refresh WHERE refresh_date = ?",
        (day,),
    ).fetchone()
    return row is not None


def _claim(day: str) -> bool:
    cursor = get_database().execute(
        """
        INSERT OR IGNORE INTO daily_refresh (refresh_date, status, started_at)
        VALUES (?, 'running', ?)
        """,
        (day, utc_now_iso()),
    )
    return cursor.rowcount == 1


def _release(day: str) -> None:
    get_database().execute(
        "DELETE FROM daily_refresh WHERE refresh_date = ? AND status = 'running'",
        (day,),
    )


def _finish(day: str, status: str, spent: int, detail: dict) -> None:
    get_database().execute(
        """
        UPDATE daily_refresh
        SET status = ?, finished_at = ?, credits_used = ?, detail_json = ?
        WHERE refresh_date = ?
        """,
        (status, utc_now_iso(), spent, json.dumps(detail, default=str), day),
    )
