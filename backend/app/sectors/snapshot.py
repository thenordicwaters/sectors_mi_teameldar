from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from app.sectors.client import SectorsClient, SectorsClientError, SectorsResponse
from app.sectors.credits import credits_used, utc_now_iso
from app.sectors.database import get_database
from app.sectors.paths import (
    COMPANIES_SCREENER_CREDITS_PER_PAGE,
    COMPANIES_SCREENER_MAX_PAGE_SIZE,
    COMPANIES_SCREENER_PATH,
    FOREIGN_FLOW_CREDITS_PER_PAGE,
    FOREIGN_FLOW_MAX_PAGE_SIZE,
    FOREIGN_FLOW_PATH,
)

logger = logging.getLogger("sectors.snapshot")

# Credit cost: 1 per page. Structured where only — never q=.
SCREENER_FIELD_PRESENCE_CLAUSE = " AND ".join(
    [
        f"({field_name} IS NOT NULL OR {field_name} IS NULL)"
        for field_name in (
            "market_cap",
            "market_cap_rank",
            "last_close_price",
            "daily_close_change",
            "pe_ttm",
            "pb_mrq",
            "ps_ttm",
            "roe_ttm",
            "yield_ttm",
            "sector",
            "sub_sector",
            "listing_board",
        )
    ]
)

FILTER_CLAUSE_CANDIDATES = [
    SCREENER_FIELD_PRESENCE_CLAUSE,
    "market_cap IS NOT NULL",
    None,
]

SECTORS_FIELD_TO_COLUMN = {
    "sector": "sector",
    "sub_sector": "sub_sector",
    "listing_board": "listing_board",
    "last_close_price": "last_close_price",
    "daily_close_change": "daily_close_change",
    "market_cap": "market_capitalization",
    "market_cap_rank": "market_capitalization_rank",
    "pe_ttm": "price_to_earnings_trailing_twelve_months",
    "pb_mrq": "price_to_book_most_recent_quarter",
    "ps_ttm": "price_to_sales_trailing_twelve_months",
    "roe_ttm": "return_on_equity_trailing_twelve_months",
    "yield_ttm": "dividend_yield_trailing_twelve_months",
}


def run_snapshot(
    *,
    force_refresh: bool = False,
    max_credits: int = 50,
    companies_only: bool = False,
    foreign_flow_only: bool = False,
) -> dict[str, int]:
    client = SectorsClient(force_refresh=force_refresh, max_credits_this_run=max_credits)
    credits_before = credits_used()
    counts = {"companies": 0, "foreign_flow": 0}
    try:
        if not foreign_flow_only:
            company_rows = snapshot_company_universe(client)
            counts["companies"] = len(company_rows)
        if not companies_only:
            flow_rows = snapshot_foreign_flow(client)
            counts["foreign_flow"] = len(flow_rows)
    finally:
        client.close()
    counts["credits_used"] = credits_used() - credits_before
    from app.sectors.repository import invalidate_derived_cache

    invalidate_derived_cache()
    return counts


def snapshot_company_universe(client: SectorsClient) -> list[dict[str, Any]]:
    query_parameters, first_page = _discover_working_filter_clause(client)
    rows = client.continue_pagination(
        COMPANIES_SCREENER_PATH,
        query_parameters,
        first_page,
        success_credit_cost_per_page=COMPANIES_SCREENER_CREDITS_PER_PAGE,
        page_size=COMPANIES_SCREENER_MAX_PAGE_SIZE,
    )
    materialized = [materialize_company_row(row) for row in rows]
    materialized = [row for row in materialized if row is not None]
    database = get_database()
    database.execute("DELETE FROM company_universe")
    database.execute_many(
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
        [
            (
                row["ticker_symbol"],
                row["company_name"],
                row["sector"],
                row["sub_sector"],
                row["listing_board"],
                row["last_close_price"],
                row["daily_close_change"],
                row["market_capitalization"],
                row["market_capitalization_rank"],
                row["price_to_earnings_trailing_twelve_months"],
                row["price_to_book_most_recent_quarter"],
                row["price_to_sales_trailing_twelve_months"],
                row["return_on_equity_trailing_twelve_months"],
                row["dividend_yield_trailing_twelve_months"],
                row["query_values_json"],
                row["fetched_at"],
            )
            for row in materialized
        ],
    )
    database.execute(
        """
        INSERT OR REPLACE INTO snapshot_meta (snapshot_name, completed_at, row_count, credits_used)
        VALUES ('company_universe', ?, ?, 0)
        """,
        (utc_now_iso(), len(materialized)),
    )
    logger.info("materialized %s companies", len(materialized))
    return materialized


def snapshot_foreign_flow(client: SectorsClient) -> list[dict[str, Any]]:
    rows = client.get_all_pages(
        FOREIGN_FLOW_PATH,
        {"order_by": "-net_foreign_inflow"},
        success_credit_cost_per_page=FOREIGN_FLOW_CREDITS_PER_PAGE,
        page_size=FOREIGN_FLOW_MAX_PAGE_SIZE,
    )
    materialized = [_materialize_foreign_flow_row(row) for row in rows]
    materialized = [row for row in materialized if row is not None]
    database = get_database()
    database.execute("DELETE FROM foreign_flow")
    database.execute_many(
        """
        INSERT INTO foreign_flow (
            ticker_symbol, trading_date, net_foreign_inflow,
            foreign_buy_value_rupiah, foreign_sell_value_rupiah
        ) VALUES (?, ?, ?, ?, ?)
        """,
        [
            (
                row["ticker_symbol"],
                row["trading_date"],
                row["net_foreign_inflow"],
                row["foreign_buy_value_rupiah"],
                row["foreign_sell_value_rupiah"],
            )
            for row in materialized
        ],
    )
    database.execute(
        """
        INSERT OR REPLACE INTO snapshot_meta (snapshot_name, completed_at, row_count, credits_used)
        VALUES ('foreign_flow', ?, ?, 0)
        """,
        (utc_now_iso(), len(materialized)),
    )
    logger.info("materialized %s foreign-flow rows", len(materialized))
    return materialized


def _discover_working_filter_clause(
    client: SectorsClient,
) -> tuple[dict[str, Any], SectorsResponse]:
    """Structured 400s are free. Reuse the first 200 page so it is not billed twice."""
    for filter_clause in FILTER_CLAUSE_CANDIDATES:
        query_parameters: dict[str, Any] = {
            "order_by": "-market_cap",
            "include_query_values": True,
        }
        if filter_clause is not None:
            query_parameters["where"] = filter_clause
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
        if response.status_code == 200:
            logger.info("using filter_clause=%s", filter_clause)
            return query_parameters, response
        if response.status_code == 400:
            logger.warning(
                "filter_clause rejected (free 400): %s",
                _error_message(response),
            )
            continue
        raise SectorsClientError(
            f"Screener probe failed {response.status_code}: {response.payload!r}"
        )
    raise SectorsClientError("No working structured screener filter_clause.")


def materialize_company_row(row: dict[str, Any]) -> dict[str, Any] | None:
    ticker_symbol = row.get("symbol")
    company_name = row.get("company_name")
    if not ticker_symbol or not company_name:
        return None
    query_values = row.get("query_values") or {}
    if not isinstance(query_values, dict):
        query_values = {}
    flattened = {
        "ticker_symbol": str(ticker_symbol),
        "company_name": str(company_name),
        "sector": None,
        "sub_sector": None,
        "listing_board": None,
        "last_close_price": None,
        "daily_close_change": None,
        "market_capitalization": None,
        "market_capitalization_rank": None,
        "price_to_earnings_trailing_twelve_months": None,
        "price_to_book_most_recent_quarter": None,
        "price_to_sales_trailing_twelve_months": None,
        "return_on_equity_trailing_twelve_months": None,
        "dividend_yield_trailing_twelve_months": None,
        "query_values_json": json.dumps(query_values),
        "fetched_at": utc_now_iso(),
    }
    for sectors_field, column_name in SECTORS_FIELD_TO_COLUMN.items():
        if sectors_field in query_values:
            flattened[column_name] = query_values[sectors_field]
    return flattened


def _materialize_foreign_flow_row(row: dict[str, Any]) -> dict[str, Any] | None:
    ticker_symbol = row.get("symbol")
    trading_date = row.get("date")
    if not ticker_symbol or not trading_date:
        return None
    return {
        "ticker_symbol": str(ticker_symbol),
        "trading_date": str(trading_date),
        "net_foreign_inflow": row.get("net_foreign_inflow"),
        "foreign_buy_value_rupiah": row.get("foreign_buy_idr"),
        "foreign_sell_value_rupiah": row.get("foreign_sell_idr"),
    }


def _error_message(response: SectorsResponse) -> str:
    payload = response.payload
    if isinstance(payload, dict):
        return str(payload.get("message") or payload.get("error") or payload)
    return str(payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Snapshot IDX screener universe and full-universe foreign flow. "
            "Structured screener is 1 credit/page (max 200). "
            "Foreign flow is 1 credit/page (max 30). "
            "Cached pages cost 0. Never uses q= (3 credits)."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass HTTP cache and spend credits again.",
    )
    parser.add_argument(
        "--max-credits",
        type=int,
        default=50,
        help="Abort if this run would spend more live credits than this.",
    )
    parser.add_argument("--companies-only", action="store_true")
    parser.add_argument("--foreign-flow-only", action="store_true")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned credit cost and exit without calling Sectors.",
    )
    arguments = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if arguments.dry_run:
        print(
            "Planned live cost if cache is empty: "
            "companies ~5 credits (limit 200) + foreign flow ~25 credits (limit 30) "
            "≈ 30 credits. Cached reruns cost 0. Cap this run at "
            f"{arguments.max_credits}."
        )
        return 0
    counts = run_snapshot(
        force_refresh=arguments.force,
        max_credits=arguments.max_credits,
        companies_only=arguments.companies_only,
        foreign_flow_only=arguments.foreign_flow_only,
    )
    print(
        "Snapshot complete: "
        f"{counts['companies']} companies, "
        f"{counts['foreign_flow']} foreign-flow rows, "
        f"{counts['credits_used']} credits this run."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
