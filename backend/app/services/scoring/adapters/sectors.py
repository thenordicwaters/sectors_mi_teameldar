from __future__ import annotations

import json
from typing import Any

from app.enrichment.yahoo import apply_yahoo_overlay, load_yahoo_overlay_rows
from app.sectors.database import get_database
from app.services.scoring.config import FINANCIAL_SECTORS, UTILITY_SUB_SECTORS
from app.services.scoring.types import StockInputs

# Phase 1 Sectors names only. Do not add guessed screener fields here.
FIELD_MAPPING = {
    "symbol": "symbol",
    "company_name": "company_name",
    "sector": "sector",
    "sub_sector": "sub_sector",
    "listing_board": "listing_board",
    "market_cap": "market_cap",
    "last_close_price": "last_close_price",
    "daily_close_change": "daily_return",
    "pe_ttm": "price_to_earnings",
    "roe_ttm": "return_on_equity",
    "net_foreign_inflow": "net_foreign_inflow",
    "foreign_buy_idr": "foreign_buy_value",
    "foreign_sell_idr": "foreign_sell_value",
}

COLUMN_FALLBACKS = {
    "ticker_symbol": "symbol",
    "company_name": "company_name",
    "sector": "sector",
    "sub_sector": "sub_sector",
    "listing_board": "listing_board",
    "market_capitalization": "market_cap",
    "last_close_price": "last_close_price",
    "daily_close_change": "daily_return",
    "price_to_earnings_trailing_twelve_months": "price_to_earnings",
    "return_on_equity_trailing_twelve_months": "return_on_equity",
    "net_foreign_inflow": "net_foreign_inflow",
    "foreign_buy_value_rupiah": "foreign_buy_value",
    "foreign_sell_value_rupiah": "foreign_sell_value",
}


def load_universe_inputs() -> list[StockInputs]:
    database = get_database()
    rows = database.execute(
        """
        SELECT
            company_universe.*,
            latest_foreign_flow.net_foreign_inflow AS net_foreign_inflow,
            latest_foreign_flow.foreign_buy_value_rupiah AS foreign_buy_value_rupiah,
            latest_foreign_flow.foreign_sell_value_rupiah AS foreign_sell_value_rupiah,
            latest_foreign_flow.trading_date AS trading_date
        FROM company_universe
        LEFT JOIN (
            SELECT
                ticker_symbol,
                net_foreign_inflow,
                foreign_buy_value_rupiah,
                foreign_sell_value_rupiah,
                trading_date
            FROM foreign_flow
            WHERE trading_date = (SELECT MAX(trading_date) FROM foreign_flow)
        ) AS latest_foreign_flow
            ON latest_foreign_flow.ticker_symbol = company_universe.ticker_symbol
        ORDER BY company_universe.ticker_symbol
        """
    ).fetchall()
    overlays = load_yahoo_overlay_rows()
    return [
        row_to_stock_inputs(dict(row), overlay=overlays.get(dict(row)["ticker_symbol"]))
        for row in rows
    ]


def row_to_stock_inputs(
    row: dict[str, Any], overlay: dict[str, Any] | None = None
) -> StockInputs:
    payload: dict[str, Any] = {}
    for column_name, attribute_name in COLUMN_FALLBACKS.items():
        if row.get(column_name) is not None:
            payload[attribute_name] = row[column_name]
    query_values = row.get("query_values_json")
    if isinstance(query_values, str) and query_values:
        decoded = json.loads(query_values)
        if isinstance(decoded, dict):
            for sectors_name, attribute_name in FIELD_MAPPING.items():
                if decoded.get(sectors_name) is not None:
                    payload[attribute_name] = decoded[sectors_name]
    if row.get("ticker_symbol"):
        payload["symbol"] = row["ticker_symbol"]
    stock = StockInputs.model_validate(_stock_kwargs(payload))
    stock = apply_yahoo_overlay(stock, overlay)
    return _apply_proxies(stock)


def _stock_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    allowed = StockInputs.model_fields
    return {key: value for key, value in payload.items() if key in allowed}


def _apply_proxies(stock: StockInputs) -> StockInputs:
    notes: list[str] = list(stock.adapter_notes)
    stock.is_financial = stock.sector in FINANCIAL_SECTORS
    stock.is_utility = stock.sub_sector in UTILITY_SUB_SECTORS
    if stock.is_suspended is None:
        notes.append(
            "Suspension flag not in cache; listing_board Watchlist is the illiquidity proxy."
        )
    if stock.listing_date is None:
        notes.append("listing_date not in cache; recent listings are not guessed.")

    if stock.roa is None and stock.return_on_equity is not None:
        stock.roa = stock.return_on_equity
        notes.append(
            "ROA proxied from roe_ttm; prior-year ROA and cash-flow tests are missing."
        )

    pe = stock.price_to_earnings
    roe = stock.return_on_equity
    if pe is not None and pe > 0:
        stock.earnings_yield = 1.0 / pe
        notes.append("Earnings yield proxied as 1/pe_ttm (EBIT/EV not in cache).")
    elif pe is not None:
        stock.earnings_yield = -1.0
        notes.append(
            "Non-positive pe_ttm treated as negative earnings yield (ranks worst)."
        )
    if roe is not None:
        stock.return_on_capital = roe
        notes.append(
            "Return on capital proxied from roe_ttm (EBIT/(NWC+NFA) not in cache)."
        )

    if stock.volume is None:
        notes.append(
            "Share volume and average traded value are not in cache; "
            "liquidity uses market_cap and listing_board only."
        )
    if stock.net_interest_margin is None or stock.non_performing_loans is None:
        notes.append(
            "NIM and NPL are not in cache; financials quality ranks available metrics only."
        )
    if stock.return_12m is None or stock.return_1m is None:
        notes.append(
            "No 1-month/1-year price change in cache; "
            "momentum uses daily_close_change as a 1-day proxy."
        )
    stock.adapter_notes = notes
    return stock
