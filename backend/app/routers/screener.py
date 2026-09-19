from fastapi import APIRouter, Query

from app.models.common import Pagination, ViewTab
from app.models.screener import ScreenerResponse

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("", response_model=ScreenerResponse)
def list_screener(
    where: str | None = None,
    order_by: str = "-score",
    view: ViewTab = ViewTab.overview,
    signal: str | None = None,
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ScreenerResponse:
    """Stub until Phase 1 loads a cached Sectors snapshot. Does not call Sectors."""
    _ = (where, order_by, signal)
    return ScreenerResponse(
        results=[],
        view=view,
        pagination=Pagination(
            total_count=0,
            showing=0,
            limit=limit,
            offset=offset,
            has_next=False,
            has_previous=offset > 0,
            next_offset=None,
            previous_offset=None if offset == 0 else max(offset - limit, 0),
        ),
    )
