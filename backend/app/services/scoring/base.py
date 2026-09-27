from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from app.services.scoring.types import MethodResult, StockInputs


@runtime_checkable
class ScoringMethod(Protocol):
    name: str
    version: str
    required_fields: tuple[str, ...]

    def applies_to(self, stock: StockInputs) -> bool:
        ...

    def score(self, stock: StockInputs, universe: Sequence[StockInputs]) -> MethodResult:
        ...


def method_result(
    *,
    method: str,
    version: str,
    score: float | None = None,
    breakdown: dict | None = None,
    reasons: list[str] | None = None,
    missing_fields: list[str] | None = None,
    applicable: bool = True,
    notes: list[str] | None = None,
) -> MethodResult:
    return MethodResult(
        method=method,
        version=version,
        score=score,
        breakdown=breakdown or {},
        reasons=reasons or [],
        missing_fields=missing_fields or [],
        applicable=applicable,
        notes=notes or [],
    )
