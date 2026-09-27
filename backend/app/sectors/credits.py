import json
import logging
from datetime import datetime, timezone

from app.config import settings
from app.sectors.database import get_database

logger = logging.getLogger("sectors.credits")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def credits_used() -> int:
    row = get_database().execute(
        "SELECT COALESCE(SUM(credits_charged), 0) AS total FROM credit_events"
    ).fetchone()
    return settings.sectors_opening_credits_used + int(row["total"])


def credits_remaining() -> int:
    return settings.sectors_credit_budget - credits_used()


def record_credit_event(
    *,
    path: str,
    status_code: int,
    credits_charged: int,
    cache_hit: bool,
) -> int:
    used_after = credits_used() + credits_charged
    get_database().execute(
        """
        INSERT INTO credit_events (
            logged_at, path, status_code, credits_charged, cache_hit, credits_used_after
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            utc_now_iso(),
            path,
            status_code,
            credits_charged,
            int(cache_hit),
            used_after,
        ),
    )
    remaining = settings.sectors_credit_budget - used_after
    cache_label = "hit" if cache_hit else "miss"
    logger.info(
        "path=%s status=%s credits=%+d used=%s remaining=%s cache=%s",
        path,
        status_code,
        credits_charged,
        used_after,
        remaining,
        cache_label,
    )
    return used_after


def recent_credit_events(limit: int = 20) -> list[dict]:
    rows = get_database().execute(
        """
        SELECT logged_at, path, status_code, credits_charged, cache_hit, credits_used_after
        FROM credit_events
        ORDER BY event_id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def charge_for_status(
    *,
    status_code: int,
    success_credit_cost: int,
    used_natural_language_query: bool,
) -> int:
    if status_code in {401, 403, 429} or status_code >= 500:
        return 0
    if status_code == 400:
        return 1 if used_natural_language_query else 0
    if status_code == 404:
        return 1
    if 200 <= status_code < 300:
        return success_credit_cost
    return 0
