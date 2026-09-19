from fastapi import APIRouter, Query

from app.models.anomalies import UnusualActivityResponse
from app.models.common import Pagination

router = APIRouter(prefix="/api/unusual", tags=["unusual"])


@router.get("", response_model=UnusualActivityResponse)
def list_unusual_activity(
    page_size: int = Query(default=20, ge=1, le=200),
    page_offset: int = Query(default=0, ge=0),
) -> UnusualActivityResponse:
    """Stub. Phase 2 will flag standard scores on cached volume and foreign flow."""
    return UnusualActivityResponse(
        results=[],
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
