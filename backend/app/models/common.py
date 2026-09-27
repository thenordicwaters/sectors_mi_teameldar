from enum import Enum

from pydantic import BaseModel, Field


class ViewTab(str, Enum):
    overview = "overview"
    valuation = "valuation"
    flow = "flow"


class SignalKind(str, Enum):
    mover = "mover"
    fifty_two_week_high = "fifty_two_week_high"
    foreign_accumulation = "foreign_accumulation"
    insider_buying = "insider_buying"


class SignalBadge(BaseModel):
    signal_kind: SignalKind
    label: str
    reason: str


class ScoreBreakdown(BaseModel):
    """Four-pillar score. Missing parts are null; overall_score is null when unranked."""

    overall_score: float | None = Field(default=None, ge=0, le=100)
    value_score: float | None = Field(default=None, ge=0, le=100)
    quality_score: float | None = Field(default=None, ge=0, le=100)
    momentum_score: float | None = Field(default=None, ge=0, le=100)
    flow_score: float | None = Field(default=None, ge=0, le=100)
    universe_rank: int | None = Field(default=None, ge=1)


class Pagination(BaseModel):
    total_count: int = Field(ge=0)
    shown_count: int = Field(ge=0)
    page_size: int = Field(ge=1, le=200)
    page_offset: int = Field(ge=0)
    has_next_page: bool
    has_previous_page: bool
    next_page_offset: int | None = None
    previous_page_offset: int | None = None
