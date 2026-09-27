from collections.abc import Sequence
from statistics import median

from app.services.scoring.base import method_result
from app.services.scoring.config import (
    FLOW_NET_RATIO_WEIGHT,
    FLOW_RELATIVE_VOLUME_WEIGHT,
    METHOD_VERSION,
)
from app.services.scoring.stats import percentile_rank
from app.services.scoring.types import MethodResult, StockInputs


class ForeignFlowMethod:
    name = "foreign_flow"
    version = METHOD_VERSION
    required_fields = ("net_foreign_inflow", "foreign_buy_value", "foreign_sell_value")

    def __init__(self) -> None:
        self._ranks_id: int | None = None
        self._by_symbol: dict[str, dict] = {}

    def applies_to(self, stock: StockInputs) -> bool:
        return _net_ratio(stock) is not None

    def score(self, stock: StockInputs, universe: Sequence[StockInputs]) -> MethodResult:
        net_ratio = _net_ratio(stock)
        if net_ratio is None:
            return method_result(
                method=self.name,
                version=self.version,
                score=None,
                applicable=False,
                reasons=["No recent foreign-flow row to rank."],
                missing_fields=_missing_flow_fields(stock),
                notes=list(stock.adapter_notes),
            )

        payload = self._universe_payload(universe).get(stock.symbol)
        notes = list(stock.adapter_notes)
        notes.append(
            "Traded value proxied as foreign_buy_value + foreign_sell_value; "
            "relative volume is foreign turnover vs universe median."
        )
        return method_result(
            method=self.name,
            version=self.version,
            score=None if payload is None else payload["score"],
            breakdown={
                "net_foreign_inflow": stock.net_foreign_inflow,
                "foreign_turnover": _foreign_turnover(stock),
                "net_ratio": net_ratio,
                "relative_volume": None if payload is None else payload["relative_volume"],
            },
            reasons=[
                f"Net foreign / foreign turnover {net_ratio:.4f}.",
                f"Flow percentile {payload['score']:.1f}."
                if payload and payload["score"] is not None
                else "Flow percentile unavailable.",
            ],
            notes=notes,
        )

    def _universe_payload(self, universe: Sequence[StockInputs]) -> dict[str, dict]:
        universe_id = id(universe)
        if self._ranks_id == universe_id:
            return self._by_symbol
        ratios = []
        turnovers = []
        symbols = []
        for member in universe:
            member_ratio = _net_ratio(member)
            member_turnover = _foreign_turnover(member)
            if member_ratio is None or member_turnover is None:
                continue
            symbols.append(member.symbol)
            ratios.append(member_ratio)
            turnovers.append(member_turnover)

        median_turnover = median(turnovers) if turnovers else None
        relative_volumes = [
            turnover / median_turnover
            if median_turnover not in (None, 0)
            else None
            for turnover in turnovers
        ]
        ratio_percentiles = percentile_rank(ratios, higher_is_better=True)
        volume_percentiles = percentile_rank(relative_volumes, higher_is_better=True)
        scores = []
        for ratio_percentile, volume_percentile in zip(
            ratio_percentiles, volume_percentiles
        ):
            if ratio_percentile is None:
                scores.append(None)
                continue
            if volume_percentile is None:
                scores.append(ratio_percentile)
                continue
            scores.append(
                FLOW_NET_RATIO_WEIGHT * ratio_percentile
                + FLOW_RELATIVE_VOLUME_WEIGHT * volume_percentile
            )
        self._by_symbol = {
            symbol: {
                "net_ratio": ratio,
                "relative_volume": relative_volume,
                "score": score,
            }
            for symbol, ratio, relative_volume, score in zip(
                symbols, ratios, relative_volumes, scores
            )
        }
        self._ranks_id = universe_id
        return self._by_symbol


def _foreign_turnover(stock: StockInputs) -> float | None:
    if stock.foreign_buy_value is None or stock.foreign_sell_value is None:
        return None
    return stock.foreign_buy_value + stock.foreign_sell_value


def _net_ratio(stock: StockInputs) -> float | None:
    if stock.net_foreign_inflow is None:
        return None
    turnover = _foreign_turnover(stock)
    if turnover in (None, 0):
        return None
    return stock.net_foreign_inflow / turnover


def _missing_flow_fields(stock: StockInputs) -> list[str]:
    missing = []
    for field_name in ForeignFlowMethod.required_fields:
        if getattr(stock, field_name) is None:
            missing.append(field_name)
    return missing
