"""Tiny labeled synthetic fixtures. Tests only. Not market data."""

from app.services.scoring.config import MIN_MARKET_CAP
from app.services.scoring.types import StockInputs

LIQUID_CAP = MIN_MARKET_CAP * 2


def synthetic_stock(symbol: str = "SYN1.JK", **overrides) -> StockInputs:
    payload = {
        "symbol": symbol,
        "company_name": f"Synthetic {symbol}",
        "sector": "Industrials",
        "sub_sector": "Industrial Goods",
        "listing_board": "Main",
        "market_cap": LIQUID_CAP,
        "is_financial": False,
        "is_utility": False,
        "is_suspended": False,
        "earnings_yield": 0.08,
        "return_on_capital": 0.15,
        "daily_return": 0.01,
        "net_foreign_inflow": 1_000_000,
        "foreign_buy_value": 4_000_000,
        "foreign_sell_value": 3_000_000,
        "return_on_equity": 0.15,
    }
    payload.update(overrides)
    return StockInputs.model_validate(payload)


def complete_piotroski(symbol: str = "PIOT.JK", *, passing: bool = True) -> StockInputs:
    if passing:
        values = dict(
            roa=0.08,
            roa_prior=0.04,
            cash_flow_from_operations=200.0,
            net_income=100.0,
            long_term_debt_ratio=0.20,
            long_term_debt_ratio_prior=0.30,
            current_ratio=2.0,
            current_ratio_prior=1.4,
            shares_outstanding=100.0,
            shares_outstanding_prior=100.0,
            gross_margin=0.40,
            gross_margin_prior=0.30,
            asset_turnover=1.2,
            asset_turnover_prior=1.0,
        )
    else:
        values = dict(
            roa=-0.02,
            roa_prior=0.04,
            cash_flow_from_operations=-10.0,
            net_income=100.0,
            long_term_debt_ratio=0.40,
            long_term_debt_ratio_prior=0.30,
            current_ratio=1.0,
            current_ratio_prior=1.4,
            shares_outstanding=120.0,
            shares_outstanding_prior=100.0,
            gross_margin=0.20,
            gross_margin_prior=0.30,
            asset_turnover=0.8,
            asset_turnover_prior=1.0,
        )
    return synthetic_stock(symbol, **values)
