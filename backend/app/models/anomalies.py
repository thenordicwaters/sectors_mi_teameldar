from enum import Enum

from pydantic import BaseModel, Field

from app.models.common import Pagination


class AnomalyKind(str, Enum):
    volume_standard_score = "volume_standard_score"
    foreign_flow_standard_score = "foreign_flow_standard_score"


class AnomalyFlag(BaseModel):
    ticker_symbol: str
    company_name: str
    anomaly_kind: AnomalyKind
    standard_score: float
    as_of_date: str = Field(description="YYYY-MM-DD")
    reason: str


class UnusualActivityResponse(BaseModel):
    results: list[AnomalyFlag]
    pagination: Pagination
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )
