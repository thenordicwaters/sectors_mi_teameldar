from collections.abc import Sequence

from app.services.scoring.base import method_result
from app.services.scoring.config import METHOD_VERSION
from app.services.scoring.stats import percentile_rank
from app.services.scoring.types import MethodResult, StockInputs

class MomentumMethod:
    name = "momentum"
    version = METHOD_VERSION
    required_fields = ("return_12m", "return_1m")

    def __init__(self) -> None:
        self._ranks_id: int | None = None
        self._ranks: dict[str, float | None] = {}

    def applies_to(self, stock: StockInputs) -> bool:
        return _momentum_value(stock)[0] is not None

    def score(self, stock: StockInputs, universe: Sequence[StockInputs]) -> MethodResult:
        value, source, missing = _momentum_value(stock)
        if value is None:
            reason = "Under 12 months of history: 12-1 momentum cannot be computed."
            if "return_12m" in missing and "return_1m" in missing and stock.daily_return is None:
                reason = (
                    "No 12-month or 1-month return in inputs, and no daily return proxy."
                )
            return method_result(
                method=self.name,
                version=self.version,
                score=None,
                applicable=False,
                breakdown={"source": source},
                reasons=[reason],
                missing_fields=missing,
                notes=list(stock.adapter_notes),
            )

        values = []
        symbols = []
        universe_id = id(universe)
        if self._ranks_id != universe_id:
            for member in universe:
                member_value, _, _ = _momentum_value(member)
                if member_value is None:
                    continue
                symbols.append(member.symbol)
                values.append(member_value)
            percentiles = percentile_rank(values, higher_is_better=True)
            self._ranks = dict(zip(symbols, percentiles))
            self._ranks_id = universe_id
        score = self._ranks.get(stock.symbol)
        notes = list(stock.adapter_notes)
        if source == "daily_return":
            notes.append(
                "12-1 not in cache; ranked daily_return as a 1-day momentum proxy."
            )

        return method_result(
            method=self.name,
            version=self.version,
            score=score,
            breakdown={
                "return_12m": stock.return_12m,
                "return_1m": stock.return_1m,
                "twelve_minus_one": value if source == "twelve_minus_one" else None,
                "daily_return": stock.daily_return,
                "source": source,
                "ranked_value": value,
            },
            reasons=[
                f"Ranked {source} {value:.4f} at percentile {score:.1f}."
                if score is not None
                else f"Ranked {source} {value:.4f}."
            ],
            notes=notes,
        )


def _momentum_value(stock: StockInputs) -> tuple[float | None, str | None, list[str]]:
    twelve_minus_one = _twelve_minus_one(stock)
    if twelve_minus_one is not None:
        return twelve_minus_one, "twelve_minus_one", []
    missing = []
    if stock.return_12m is None:
        missing.append("return_12m")
    if stock.return_1m is None:
        missing.append("return_1m")
    if stock.daily_return is not None:
        return stock.daily_return, "daily_return", missing
    if stock.listing_date is not None:
        missing.append("listing_date")
    return None, None, missing


def _twelve_minus_one(stock: StockInputs) -> float | None:
    if stock.return_12m is None or stock.return_1m is None:
        return None
    if stock.return_1m == -1:
        return None
    return (1 + stock.return_12m) / (1 + stock.return_1m) - 1
