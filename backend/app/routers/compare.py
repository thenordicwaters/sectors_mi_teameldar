from fastapi import APIRouter, HTTPException, Query

from app.models.compare import CompareResponse

router = APIRouter(prefix="/api/compare", tags=["compare"])


@router.get("", response_model=CompareResponse)
def compare_stocks(
    symbols: str = Query(..., description="Comma-separated, 2 or 3 IDX symbols."),
) -> CompareResponse:
    """Stub until Phase 2 fills metrics from cached rows."""
    parts = [s.strip().upper().removesuffix(".JK") for s in symbols.split(",") if s.strip()]
    if not (2 <= len(parts) <= 3):
        raise HTTPException(status_code=400, detail="Compare 2 or 3 symbols.")
    tagged = [f"{s}.JK" for s in parts]
    return CompareResponse(
        symbols=tagged,
        company_names={s: "" for s in tagged},
        metrics=[],
    )
