from pydantic import BaseModel, Field


class CompareRequest(BaseModel):
    symbols: list[str] = Field(min_length=2, max_length=3)


class CompareMetricRow(BaseModel):
    metric: str
    values: dict[str, float | str | None]


class CompareResponse(BaseModel):
    symbols: list[str]
    company_names: dict[str, str]
    metrics: list[CompareMetricRow]
    disclaimer: str = (
        "Information and analysis only. Not investment advice."
    )
