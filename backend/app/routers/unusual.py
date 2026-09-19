from fastapi import APIRouter, Query

from app.models.anomalies import UnusualActivityResponse
from app.models.common import Pagination

router = APIRouter(prefix="/api/unusual", tags=["unusual"])


@router.get("", response_model=UnusualActivityResponse)
def list_unusual(
    limit: int = Query(default=20, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> UnusualActivityResponse:
    """Stub. Phase 2 will flag z-scores on cached volume and foreign flow."""
    return UnusualActivityResponse(
        results=[],
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
