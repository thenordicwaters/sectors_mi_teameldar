from fastapi import APIRouter, Query

from app.models.anomalies import AnomalyKind, UnusualActivityResponse
from app.sectors.repository import list_unusual_activity_page
from app.services.anomalies import (
    FOREIGN_FLOW_STANDARD_SCORE_THRESHOLD,
    VOLUME_STANDARD_SCORE_THRESHOLD,
)

DETECTION_FLOOR = min(
    VOLUME_STANDARD_SCORE_THRESHOLD,
    FOREIGN_FLOW_STANDARD_SCORE_THRESHOLD
)

router = APIRouter(prefix="/api/unusual", tags=["unusual"])

@router.get("", response_model=UnusualActivityResponse)
def list_unusual_activity(
    anomaly_kind: AnomalyKind | None = None,
    min_standard_score: float = Query(
        default=DETECTION_FLOOR,
        ge=DETECTION_FLOOR,
        le=100,
        description="Tighten only: detection already stops at the floor.",
    ),
    page_size: int = Query(default=20, ge=1, le=200),
    page_offset: int = Query(default=0, ge=0),
) -> UnusualActivityResponse:
    """Standard scores on cached volume and foreign flow. 0 Sectors credits."""
    return list_unusual_activity_page(
        anomaly_kind=None if anomaly_kind is None else anomaly_kind.value,
        min_standard_score=min_standard_score,
        page_size=page_size,
        page_offset=page_offset,
    )
