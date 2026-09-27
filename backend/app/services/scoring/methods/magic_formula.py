from collections.abc import Sequence

from app.services.scoring.base import method_result
from app.services.scoring.config import (
    METHOD_VERSION,
    MIN_AVERAGE_TRADED_VALUE,
    MIN_MARKET_CAP,
)
from app.services.scoring.stats import percentile_rank
from app.services.scoring.types import MethodResult, StockInputs


class MagicFormulaMethod:
    name = "magic_formula"
    version = METHOD_VERSION
    required_fields = (
        "ebit",
        "enterprise_value",
        "net_working_capital",
        "net_fixed_assets",
        "earnings_yield",
        "return_on_capital",
    )

    def __init__(self) -> None:
        self._ranks_id: int | None = None
        self._ranks: dict[str, dict] = {}

    def applies_to(self, stock: StockInputs) -> bool:
        if stock.is_financial or stock.is_utility:
            return False
        if stock.is_suspended is True:
            return False
        if stock.market_cap is None or stock.market_cap < MIN_MARKET_CAP:
            return False
        if (
            MIN_AVERAGE_TRADED_VALUE is not None
            and stock.average_traded_value is not None
            and stock.average_traded_value < MIN_AVERAGE_TRADED_VALUE
        ):
            return False
        return True

    def score(self, stock: StockInputs, universe: Sequence[StockInputs]) -> MethodResult:
        if not self.applies_to(stock):
            return method_result(
                method=self.name,
                version=self.version,
                applicable=False,
                reasons=[_exclusion_reason(stock)],
                missing_fields=_missing_formula_fields(stock),
            )

        ranks = self._formula_ranks(universe)
        payload = ranks.get(stock.symbol)
        if payload is None:
            return method_result(
                method=self.name,
                version=self.version,
                score=None,
                applicable=True,
                reasons=["Earnings yield or return on capital could not be computed."],
                missing_fields=_missing_formula_fields(stock),
            )
        return method_result(
            method=self.name,
            version=self.version,
            score=payload["percentile"],
            breakdown=payload,
            reasons=[
                f"Earnings yield {payload['earnings_yield']:.4f} "
                f"(rank {payload['earnings_yield_rank']:.1f}).",
                f"Return on capital {payload['return_on_capital']:.4f} "
                f"(rank {payload['return_on_capital_rank']:.1f}).",
                f"Combined rank {payload['combined_rank']:.1f}; "
                f"percentile {payload['percentile']:.1f} (best = 100).",
            ],
        )

    def _formula_ranks(self, universe: Sequence[StockInputs]) -> dict[str, dict]:
        universe_id = id(universe)
        if self._ranks_id == universe_id:
            return self._ranks
        eligible: list[StockInputs] = []
        earnings_yields: list[float] = []
        returns_on_capital: list[float] = []
        for stock in universe:
            if not self.applies_to(stock):
                continue
            earnings_yield = _earnings_yield(stock)
            return_on_capital = _return_on_capital(stock)
            if earnings_yield is None or return_on_capital is None:
                continue
            eligible.append(stock)
            earnings_yields.append(earnings_yield)
            returns_on_capital.append(return_on_capital)

        if not eligible:
            self._ranks_id = universe_id
            self._ranks = {}
            return self._ranks

        yield_percentiles = percentile_rank(earnings_yields, higher_is_better=True)
        roc_percentiles = percentile_rank(returns_on_capital, higher_is_better=True)
        count = len(eligible)
        yield_ranks = [
            None if percentile is None else (count - 1) * (1 - percentile / 100) + 1
            for percentile in yield_percentiles
        ]
        roc_ranks = [
            None if percentile is None else (count - 1) * (1 - percentile / 100) + 1
            for percentile in roc_percentiles
        ]
        combined = [
            (yield_rank or 0) + (roc_rank or 0)
            for yield_rank, roc_rank in zip(yield_ranks, roc_ranks)
        ]
        combined_percentiles = percentile_rank(combined, higher_is_better=False)

        ranked = {}
        for index, stock in enumerate(eligible):
            ranked[stock.symbol] = {
                "earnings_yield": earnings_yields[index],
                "return_on_capital": returns_on_capital[index],
                "earnings_yield_rank": _round_rank(yield_ranks[index]),
                "return_on_capital_rank": _round_rank(roc_ranks[index]),
                "combined_rank": _round_rank(combined[index]),
                "percentile": None
                if combined_percentiles[index] is None
                else round(combined_percentiles[index], 4),
            }
        self._ranks_id = universe_id
        self._ranks = ranked
        return ranked


def _earnings_yield(stock: StockInputs) -> float | None:
    if stock.earnings_yield is not None:
        return stock.earnings_yield
    if stock.ebit is None or stock.enterprise_value in (None, 0):
        return None
    return stock.ebit / stock.enterprise_value


def _return_on_capital(stock: StockInputs) -> float | None:
    if stock.return_on_capital is not None:
        return stock.return_on_capital
    if stock.ebit is None:
        return None
    capital = (stock.net_working_capital or 0) + (stock.net_fixed_assets or 0)
    if capital == 0:
        return None
    return stock.ebit / capital


def _missing_formula_fields(stock: StockInputs) -> list[str]:
    if _earnings_yield(stock) is not None and _return_on_capital(stock) is not None:
        return []
    missing = []
    if _earnings_yield(stock) is None:
        if stock.ebit is None:
            missing.append("ebit")
        if stock.enterprise_value in (None, 0):
            missing.append("enterprise_value")
        if stock.earnings_yield is None:
            missing.append("earnings_yield")
    if _return_on_capital(stock) is None:
        if stock.return_on_capital is None:
            missing.append("return_on_capital")
        if stock.net_working_capital is None and stock.net_fixed_assets is None:
            missing.extend(["net_working_capital", "net_fixed_assets"])
    return missing


def _exclusion_reason(stock: StockInputs) -> str:
    if stock.is_financial:
        return "Magic Formula excludes financials."
    if stock.is_utility:
        return "Magic Formula excludes utilities."
    if stock.is_suspended is True:
        return "Magic Formula excludes suspended stocks."
    if stock.market_cap is None or stock.market_cap < MIN_MARKET_CAP:
        return f"Market cap below minimum ({MIN_MARKET_CAP:.0f} IDR)."
    if MIN_AVERAGE_TRADED_VALUE is not None and (
        stock.average_traded_value is not None
        and stock.average_traded_value < MIN_AVERAGE_TRADED_VALUE
    ):
        return f"Average traded value below minimum ({MIN_AVERAGE_TRADED_VALUE:.0f} IDR)."
    return "Not eligible for Magic Formula."


def _round_rank(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)
