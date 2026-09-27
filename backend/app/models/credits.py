from pydantic import BaseModel, Field


class CreditEvent(BaseModel):
    logged_at: str
    path: str
    status_code: int
    credits_charged: int
    cache_hit: bool
    credits_used_after: int


class CreditStatus(BaseModel):
    credits_used: int = Field(ge=0)
    credit_budget: int = Field(ge=0)
    credits_remaining: int
    last_events: list[CreditEvent]
    disclaimer: str = "Information and analysis only. Not investment advice."
