from fastapi import APIRouter, Query

from app.config import settings
from app.models.credits import CreditEvent, CreditStatus
from app.sectors.credits import credits_remaining, credits_used, recent_credit_events

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("", response_model=CreditStatus)
def get_credit_status(
    event_limit: int = Query(default=20, ge=1, le=100),
) -> CreditStatus:
    events = [
        CreditEvent(
            logged_at=row["logged_at"],
            path=row["path"],
            status_code=row["status_code"],
            credits_charged=row["credits_charged"],
            cache_hit=bool(row["cache_hit"]),
            credits_used_after=row["credits_used_after"],
        )
        for row in recent_credit_events(event_limit)
    ]
    return CreditStatus(
        credits_used=credits_used(),
        credit_budget=settings.sectors_credit_budget,
        credits_remaining=credits_remaining(),
        last_events=events,
    )
