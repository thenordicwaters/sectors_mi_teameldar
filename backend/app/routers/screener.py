from fastapi import APIRouter, Query

from app.models.common import Pagination, ViewTab
from app.models.screener import ScreenerQuery, ScreenerResponse

router = APIRouter(prefix="/api/screener", tags=["screener"])


@router.get("", response_model=ScreenerResponse)
def list_screener_results(
    filter_clause: str | None = None,
    sort_by: str = "-overall_score",
    view_tab: ViewTab = ViewTab.overview,
    signal_filter: str | None = None,
    page_size: int = Query(default=20, ge=1, le=200),
    page_offset: int = Query(default=0, ge=0),
) -> ScreenerResponse:
    """Stub until Phase 1 loads a cached Sectors snapshot. Does not call Sectors."""
    ScreenerQuery(
        filter_clause=filter_clause,
        sort_by=sort_by,
        view_tab=view_tab,
        signal_filter=signal_filter,
        page_size=page_size,
        page_offset=page_offset,
    )
    return ScreenerResponse(
        results=[],
        view_tab=view_tab,
        pagination=Pagination(
            total_count=0,
            shown_count=0,
            page_size=page_size,
            page_offset=page_offset,
            has_next_page=False,
            has_previous_page=page_offset > 0,
            next_page_offset=None,
            previous_page_offset=(
                None if page_offset == 0 else max(page_offset - page_size, 0)
            ),
        ),
    )
