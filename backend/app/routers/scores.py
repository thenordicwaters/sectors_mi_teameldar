from fastapi import APIRouter, HTTPException, Query

from app.services.scoring.adapters.sectors import load_universe_inputs
from app.services.scoring.config import DEFAULT_WEIGHTS
from app.services.scoring.service import ScoringService
from app.services.scoring.types import CompositeResult, ScoresResponse, Weights

router = APIRouter(prefix="/api/scores", tags=["scores"])
_service = ScoringService()


@router.get("", response_model=ScoresResponse)
def list_scores(
    quality: float | None = Query(default=None, ge=0),
    value: float | None = Query(default=None, ge=0),
    momentum: float | None = Query(default=None, ge=0),
    flow: float | None = Query(default=None, ge=0),
) -> ScoresResponse:
    """Score the cached universe. Does not call Sectors (0 credits)."""
    weights = _weights_from_query(quality, value, momentum, flow)
    results = _service.score_universe(load_universe_inputs(), weights)
    ranked_count = sum(1 for result in results if result.rank is not None)
    return ScoresResponse(
        results=results,
        weights=weights,
        universe_size=len(results),
        ranked_count=ranked_count,
    )


@router.get("/{symbol}", response_model=CompositeResult)
def get_score(
    symbol: str,
    quality: float | None = Query(default=None, ge=0),
    value: float | None = Query(default=None, ge=0),
    momentum: float | None = Query(default=None, ge=0),
    flow: float | None = Query(default=None, ge=0),
) -> CompositeResult:
    """Score one cached symbol against the universe. Does not call Sectors (0 credits)."""
    weights = _weights_from_query(quality, value, momentum, flow)
    normalized = _normalize_symbol(symbol)
    results = _service.score_universe(load_universe_inputs(), weights)
    for result in results:
        if result.symbol == normalized:
            return result
    raise HTTPException(status_code=404, detail=f"{normalized} is not in the cached universe.")


def _weights_from_query(
    quality: float | None,
    value: float | None,
    momentum: float | None,
    flow: float | None,
) -> Weights:
    return Weights(
        quality=DEFAULT_WEIGHTS.quality if quality is None else quality,
        value=DEFAULT_WEIGHTS.value if value is None else value,
        momentum=DEFAULT_WEIGHTS.momentum if momentum is None else momentum,
        flow=DEFAULT_WEIGHTS.flow if flow is None else flow,
    )


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not normalized.endswith(".JK"):
        normalized = f"{normalized}.JK"
    return normalized
