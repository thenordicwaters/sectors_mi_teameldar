from collections.abc import Mapping, Sequence

from app.services.scoring.config import (
    ILLIQUID_LISTING_BOARDS,
    METHOD_VERSION,
    MIN_AVERAGE_TRADED_VALUE,
    MIN_COMPOSITE_PARTS,
    MIN_MARKET_CAP,
    SECTOR_PEER_MINIMUM,
)
from app.services.scoring.stats import percentile_rank
from app.services.scoring.types import (
    ComponentScores,
    CompositeResult,
    MethodResult,
    StockInputs,
    Weights,
)

QUALITY_METHOD_FINANCIALS = "financials_quality"
QUALITY_METHOD_NON_FINANCIALS = "piotroski"
VALUE_METHOD = "magic_formula"
MOMENTUM_METHOD = "momentum"
FLOW_METHOD = "foreign_flow"


class CompositeMethod:
    name = "composite"
    version = METHOD_VERSION
    required_fields = ()

    def applies_to(self, stock: StockInputs) -> bool:
        return True

    def score(self, stock: StockInputs, universe: Sequence[StockInputs]) -> MethodResult:
        del stock, universe
        raise RuntimeError("CompositeMethod.combine is the entry point, not score().")

    def combine(
        self,
        stocks: Sequence[StockInputs],
        method_results: Mapping[str, Mapping[str, MethodResult]],
        weights: Weights,
    ) -> list[CompositeResult]:
        value_scores = _sector_aware_value_scores(stocks, method_results)
        results: list[CompositeResult] = []
        for stock in stocks:
            per_stock = method_results[stock.symbol]
            quality = _quality_score(stock, per_stock)
            value = value_scores.get(stock.symbol)
            momentum = _method_score(per_stock.get(MOMENTUM_METHOD))
            flow = _method_score(per_stock.get(FLOW_METHOD))
            components = ComponentScores(
                quality=quality,
                value=value,
                momentum=momentum,
                flow=flow,
            )
            available = {
                name: score
                for name, score in components.model_dump().items()
                if score is not None
            }
            coverage = len(available) / 4
            excluded_reason = _exclusion_reason(stock)
            notes = list(stock.adapter_notes)
            score = None
            weights_used: dict[str, float] = {}
            if excluded_reason is None:
                if len(available) < MIN_COMPOSITE_PARTS:
                    excluded_reason = (
                        f"Fewer than {MIN_COMPOSITE_PARTS} score parts "
                        f"({len(available)} available)."
                    )
                else:
                    raw_weights = {
                        name: getattr(weights, name) for name in available
                    }
                    weight_total = sum(raw_weights.values())
                    if weight_total <= 0:
                        excluded_reason = "All available-part weights are zero."
                    else:
                        weights_used = {
                            name: value / weight_total * 100
                            for name, value in raw_weights.items()
                        }
                        score = sum(
                            available[name] * raw_weights[name] / weight_total
                            for name in available
                        )
                        notes.append(
                            "Weighted average of available parts; missing parts re-weighted."
                        )
            results.append(
                CompositeResult(
                    symbol=stock.symbol,
                    score=None if score is None else round(float(score), 4),
                    rank=None,
                    components=components,
                    methods=dict(per_stock),
                    coverage=coverage,
                    excluded_reason=excluded_reason,
                    notes=notes,
                    weights_used=weights_used,
                )
            )

        ranked = sorted(
            [result for result in results if result.score is not None],
            key=lambda result: (-result.score, result.symbol),
        )
        rank_by_symbol = {
            result.symbol: index for index, result in enumerate(ranked, start=1)
        }

        for result in results:
            result.rank = rank_by_symbol.get(result.symbol)
        return results


def _quality_score(
    stock: StockInputs, per_stock: Mapping[str, MethodResult]
) -> float | None:
    if stock.is_financial:
        return _method_score(per_stock.get(QUALITY_METHOD_FINANCIALS))
    piotroski = per_stock.get(QUALITY_METHOD_NON_FINANCIALS)
    raw = _method_score(piotroski)
    if raw is None:
        return None
    return raw / 9 * 100


def _method_score(result: MethodResult | None) -> float | None:
    if result is None or not result.applicable:
        return None
    return result.score


def _sector_aware_value_scores(
    stocks: Sequence[StockInputs],
    method_results: Mapping[str, Mapping[str, MethodResult]],
) -> dict[str, float | None]:
    raw_scores = []
    sectors = []
    symbols = []
    for stock in stocks:
        value = _method_score(method_results[stock.symbol].get(VALUE_METHOD))
        if value is None:
            continue
        symbols.append(stock.symbol)
        raw_scores.append(value)
        sectors.append(stock.sector)
    if not symbols:
        return {}

    counts: dict[str | None, int] = {}
    for sector in sectors:
        counts[sector] = counts.get(sector, 0) + 1
    group = [
        sector if counts.get(sector, 0) >= SECTOR_PEER_MINIMUM else None
        for sector in sectors
    ]
    ranked = percentile_rank(raw_scores, higher_is_better=True, group=group)
    return dict(zip(symbols, ranked))


def _exclusion_reason(stock: StockInputs) -> str | None:
    if stock.is_suspended is True:
        return "Suspended."
    if stock.listing_board in ILLIQUID_LISTING_BOARDS:
        return (
            f"listing_board {stock.listing_board} (illiquid / special-monitoring proxy; "
            "suspension flag not in cache)."
        )
    if stock.market_cap is None or stock.market_cap < MIN_MARKET_CAP:
        return f"Market cap below minimum ({MIN_MARKET_CAP:.0f} IDR)."
    if (
        MIN_AVERAGE_TRADED_VALUE is not None
        and stock.average_traded_value is not None
        and stock.average_traded_value < MIN_AVERAGE_TRADED_VALUE
    ):
        return (
            f"Average traded value below minimum ({MIN_AVERAGE_TRADED_VALUE:.0f} IDR)."
        )
    return None
