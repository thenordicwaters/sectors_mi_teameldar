from enum import Enum

from pydantic import BaseModel, Field

from app.models.common import Pagination


class AnomalyKind(str, Enum):
    volume_zscore = "volume_zscore"
    foreign_flow_zscore = "foreign_flow_zscore"


class AnomalyFlag(BaseModel):
    symbol: str
    company_name: str
    kind: AnomalyKind
    z_score: float
    as_of: str = Field(description="YYYY-MM-DD")
    reason: str


class UnusualActivityResponse(BaseModel):
    results: list[AnomalyFlag]
    pagination: Pagination
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )
