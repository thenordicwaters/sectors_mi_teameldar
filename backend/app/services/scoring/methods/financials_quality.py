from collections.abc import Sequence

from app.services.scoring.base import method_result
from app.services.scoring.config import METHOD_VERSION
from app.services.scoring.stats import percentile_rank
from app.services.scoring.types import MethodResult, StockInputs


class FinancialsQualityMethod:
    name = "financials_quality"
    version = METHOD_VERSION
    required_fields = ("return_on_equity", "net_interest_margin", "non_performing_loans")

    def __init__(self) -> None:
        self._ranks_id: int | None = None
        self._by_symbol: dict[str, dict] = {}

    def applies_to(self, stock: StockInputs) -> bool:
        return stock.is_financial

    def score(self, stock: StockInputs, universe: Sequence[StockInputs]) -> MethodResult:
        if not self.applies_to(stock):
            return method_result(
                method=self.name,
                version=self.version,
                applicable=False,
                reasons=["financials_quality applies only to banks and other financials."],
            )

        payload = self._universe_payload(universe).get(stock.symbol, {})
        score = payload.get("score")
        missing = [
            field_name
            for field_name in self.required_fields
            if getattr(stock, field_name) is None
        ]
        notes = list(stock.adapter_notes)
        if missing:
            notes.append(
                "Ranked only on available financial-quality metrics; missing: "
                + ", ".join(missing)
            )
        if score is None:
            return method_result(
                method=self.name,
                version=self.version,
                score=None,
                breakdown=payload,
                reasons=["No ROE, net interest margin, or NPL to rank within financials."],
                missing_fields=missing,
                notes=notes,
            )
        return method_result(
            method=self.name,
            version=self.version,
            score=score,
            breakdown={
                **payload,
                "return_on_equity": stock.return_on_equity,
                "net_interest_margin": stock.net_interest_margin,
                "non_performing_loans": stock.non_performing_loans,
            },
            reasons=[
                f"Financials-only quality percentile {score:.1f} "
                f"from {payload.get('parts_used', 0)} metric(s)."
            ],
            missing_fields=missing,
            notes=notes,
        )

    def _universe_payload(self, universe: Sequence[StockInputs]) -> dict[str, dict]:
        universe_id = id(universe)
        if self._ranks_id == universe_id:
            return self._by_symbol
        peers = [member for member in universe if member.is_financial]
        roe_percentiles = percentile_rank(
            [member.return_on_equity for member in peers],
            higher_is_better=True,
        )
        nim_percentiles = percentile_rank(
            [member.net_interest_margin for member in peers],
            higher_is_better=True,
        )
        npl_percentiles = percentile_rank(
            [member.non_performing_loans for member in peers],
            higher_is_better=False,
        )
        self._by_symbol = {}
        for index, member in enumerate(peers):
            parts = [
                value
                for value in (
                    roe_percentiles[index],
                    nim_percentiles[index],
                    npl_percentiles[index],
                )
                if value is not None
            ]
            self._by_symbol[member.symbol] = {
                "roe_percentile": roe_percentiles[index],
                "nim_percentile": nim_percentiles[index],
                "npl_percentile": npl_percentiles[index],
                "score": None if not parts else sum(parts) / len(parts),
                "parts_used": len(parts),
            }
        self._ranks_id = universe_id
        return self._by_symbol
