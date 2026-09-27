from collections.abc import Sequence

from app.services.scoring.config import DEFAULT_WEIGHTS
from app.services.scoring.methods.composite import CompositeMethod
from app.services.scoring.registry import registered_methods
from app.services.scoring.types import CompositeResult, StockInputs, Weights

class ScoringService:
    """Only public scoring entry point: StockInputs universe in, CompositeResults out."""

    def __init__(self, methods: Sequence | None = None) -> None:
        self._methods = list(methods) if methods is not None else registered_methods()
        self._composite = CompositeMethod()

    def score_universe(
        self,
        stocks: Sequence[StockInputs],
        weights: Weights | None = None,
    ) -> list[CompositeResult]:
        resolved_weights = weights or DEFAULT_WEIGHTS
        method_results: dict[str, dict] = {stock.symbol: {} for stock in stocks}
        for method in self._methods:
            for stock in stocks:
                method_results[stock.symbol][method.name] = method.score(stock, stocks)
        breakpoint()
        return sorted(
            self._composite.combine(stocks, method_results, resolved_weights),
            key=lambda result: (result.rank is None, result.rank or 0, result.symbol),
        )
