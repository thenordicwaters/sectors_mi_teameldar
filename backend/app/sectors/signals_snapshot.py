from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta
from typing import Any

from app.sectors.client import SectorsClient, SectorsClientError
from app.sectors.credits import credits_used, utc_now_iso
from app.sectors.database import get_database
from app.sectors.paths import (
    COMPANIES_SCREENER_CREDITS_PER_PAGE,
    COMPANIES_SCREENER_MAX_PAGE_SIZE,
    COMPANIES_SCREENER_PATH,
    FILINGS_CREDITS_PER_PAGE,
    FILINGS_MAX_PAGE_SIZE,
    FILINGS_PATH,
)

logger = logging.getLogger("sectors.signals_snapshot")

FIFTY_TWO_WEEK_HIGH_WHERE = "tags in ['52-w-high']"
INSIDER_LOOKBACK_DAYS = 30


def run_signals_snapshot(
    *,
    force_refresh: bool = False,
    max_credits: int = 8,
) -> dict[str, int]:
    client = SectorsClient(force_refresh=force_refresh, max_credits_this_run=max_credits)
    credits_before = credits_used()
    counts = {"fifty_two_week_high": 0, "insider_filings": 0}
    try:
        counts["fifty_two_week_high"] = snapshot_fifty_two_week_highs(client)
        counts["insider_filings"] = snapshot_insider_buys(client)
    finally:
        client.close()
    counts["credits_used"] = credits_used() - credits_before
    from app.sectors.repository import invalidate_derived_cache

    invalidate_derived_cache()
    return counts


def snapshot_fifty_two_week_highs(client: SectorsClient) -> int:
    query_parameters = {
        "where": FIFTY_TWO_WEEK_HIGH_WHERE,
        "order_by": "-market_cap",
        "include_query_values": True,
    }
    first_page_query = {
        **query_parameters,
        "limit": COMPANIES_SCREENER_MAX_PAGE_SIZE,
        "offset": 0,
    }
    response = client.get(
        COMPANIES_SCREENER_PATH,
        first_page_query,
        success_credit_cost=COMPANIES_SCREENER_CREDITS_PER_PAGE,
    )
    if response.status_code == 400:
        logger.warning("52-w-high where clause rejected (free 400): %s", response.payload)
        return 0
    if response.status_code != 200:
        raise SectorsClientError(
            f"52-w-high screener failed {response.status_code}: {response.payload!r}"
        )
    rows = client.continue_pagination(
        COMPANIES_SCREENER_PATH,
        query_parameters,
        response,
        success_credit_cost_per_page=COMPANIES_SCREENER_CREDITS_PER_PAGE,
        page_size=COMPANIES_SCREENER_MAX_PAGE_SIZE,
    )
    materialized = []
    fetched_at = utc_now_iso()
    for row in rows:
        ticker_symbol = row.get("symbol")
        if not ticker_symbol:
            continue
        query_values = row.get("query_values") if isinstance(row.get("query_values"), dict) else {}
        materialized.append(
            (
                str(ticker_symbol),
                query_values.get("last_close_price") or row.get("last_close_price"),
                fetched_at,
            )
        )
    database = get_database()
    database.execute("DELETE FROM fifty_two_week_high_flags")
    if materialized:
        database.execute_many(
            """
            INSERT INTO fifty_two_week_high_flags (ticker_symbol, last_close_price, fetched_at)
            VALUES (?, ?, ?)
            """,
            materialized,
        )
    database.execute(
        """
        INSERT OR REPLACE INTO snapshot_meta (snapshot_name, completed_at, row_count, credits_used)
        VALUES ('fifty_two_week_high', ?, ?, 0)
        """,
        (fetched_at, len(materialized)),
    )
    logger.info("materialized %s 52-w-high flags", len(materialized))
    return len(materialized)


def snapshot_insider_buys(client: SectorsClient) -> int:
    start_date = (date.today() - timedelta(days=INSIDER_LOOKBACK_DAYS)).isoformat()
    rows = client.get_all_pages(
        FILINGS_PATH,
        {
            "transaction_type": "buy",
            "holder_type": "insider",
            "start": start_date,
        },
        success_credit_cost_per_page=FILINGS_CREDITS_PER_PAGE,
        page_size=FILINGS_MAX_PAGE_SIZE,
    )
    materialized = []
    for row in rows:
        ticker_symbol = _normalize_symbol(row.get("symbol"))
        if ticker_symbol is None:
            continue
        if str(row.get("transaction_type") or "").lower() != "buy":
            continue
        materialized.append(
            (
                ticker_symbol,
                str(row.get("timestamp") or ""),
                row.get("holder_name"),
                row.get("holder_type"),
                row.get("transaction_type"),
                row.get("amount_transaction"),
                row.get("transaction_value"),
                row.get("title"),
                row.get("source"),
            )
        )
    database = get_database()
    database.execute("DELETE FROM insider_filings")
    if materialized:
        database.execute_many(
            """
            INSERT INTO insider_filings (
                ticker_symbol, filed_at, holder_name, holder_type, transaction_type,
                amount_transaction, transaction_value, title, source_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            materialized,
        )
    database.execute(
        """
        INSERT OR REPLACE INTO snapshot_meta (snapshot_name, completed_at, row_count, credits_used)
        VALUES ('insider_filings', ?, ?, 0)
        """,
        (utc_now_iso(), len(materialized)),
    )
    logger.info("materialized %s insider buy filings", len(materialized))
    return len(materialized)


def _normalize_symbol(symbol: Any) -> str | None:
    if not symbol:
        return None
    normalized = str(symbol).strip().upper()
    if not normalized.endswith(".JK"):
        normalized = f"{normalized}.JK"
    if len(normalized) != 7:
        return None
    return normalized


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Snapshot Sectors 52-w-high tags (1 credit/page) and recent insider "
            "buy filings (1 credit/page, max 30). Cached reruns cost 0. "
            "Does not call top-changes (1 per classification×period, 10 if default)."
        )
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--max-credits", type=int, default=8)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    if arguments.dry_run:
        print(
            "Planned live cost if cache is empty: "
            "52-w-high screener ~1 credit + insider filings ~1–4 credits. "
            f"Cap this run at {arguments.max_credits}."
        )
        return 0
    counts = run_signals_snapshot(
        force_refresh=arguments.force,
        max_credits=arguments.max_credits,
    )
    print(
        "Signals snapshot complete: "
        f"{counts['fifty_two_week_high']} 52-w-high flags, "
        f"{counts['insider_filings']} insider buys, "
        f"{counts['credits_used']} credits this run."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
