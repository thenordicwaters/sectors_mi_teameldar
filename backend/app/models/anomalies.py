from enum import Enum

from pydantic import BaseModel, Field

from app.models.common import Pagination


class AnomalyKind(str, Enum):
    volume_standard_score = "volume_standard_score"
    foreign_flow_standard_score = "foreign_flow_standard_score"


class AnomalyFlag(BaseModel):
    """One unusual-activity flag. `standard_score` is signed; `reason` is the sentence."""

    ticker_symbol: str
    company_name: str
    anomaly_kind: AnomalyKind
    label: str
    standard_score: float
    observed_value: float | None = None
    baseline_value: float | None = None
    threshold: float
    as_of_date: str = Field(description="YYYY-MM-DD")
    reason: str


class UnusualActivityResponse(BaseModel):
    results: list[AnomalyFlag]
    pagination: Pagination
    method_notes: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )
