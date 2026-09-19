from enum import Enum

from pydantic import BaseModel, Field


class ViewTab(str, Enum):
    overview = "overview"
    valuation = "valuation"
    flow = "flow"


class SignalKind(str, Enum):
    mover = "mover"
    week_52_high = "week_52_high"
    foreign_accumulation = "foreign_accumulation"
    insider_buying = "insider_buying"


class SignalBadge(BaseModel):
    kind: SignalKind
    label: str
    reason: str


class ScoreBreakdown(BaseModel):
    """Four-pillar score. Weights are decided in Phase 2; placeholders are 0 until then."""

    overall: float = Field(ge=0, le=100)
    value: float = Field(ge=0, le=100)
    quality: float = Field(ge=0, le=100)
    momentum: float = Field(ge=0, le=100)
    flow: float = Field(ge=0, le=100)
    rank: int | None = Field(default=None, ge=1)


class Pagination(BaseModel):
    total_count: int = Field(ge=0)
    showing: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)
    has_next: bool
    has_previous: bool
    next_offset: int | None = None
    previous_offset: int | None = None
