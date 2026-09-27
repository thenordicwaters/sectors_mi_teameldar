from typing import Any

from pydantic import BaseModel, Field


class Weights(BaseModel):
    quality: float = Field(default=30, ge=0)
    value: float = Field(default=25, ge=0)
    momentum: float = Field(default=25, ge=0)
    flow: float = Field(default=20, ge=0)

    def as_dict(self) -> dict[str, float]:
        return {
            "quality": self.quality,
            "value": self.value,
            "momentum": self.momentum,
            "flow": self.flow,
        }


class StockInputs(BaseModel):
    """Normalized, source-agnostic inputs. Methods must not depend on Sectors names."""

    symbol: str
    company_name: str | None = None
    sector: str | None = None
    sub_sector: str | None = None
    listing_board: str | None = None
    market_cap: float | None = None
    last_close_price: float | None = None
    is_financial: bool = False
    is_utility: bool = False
    is_suspended: bool | None = None
    listing_date: str | None = None

    roa: float | None = None
    roa_prior: float | None = None
    cash_flow_from_operations: float | None = None
    cash_flow_from_operations_prior: float | None = None
    net_income: float | None = None
    long_term_debt_ratio: float | None = None
    long_term_debt_ratio_prior: float | None = None
    current_ratio: float | None = None
    current_ratio_prior: float | None = None
    shares_outstanding: float | None = None
    shares_outstanding_prior: float | None = None
    gross_margin: float | None = None
    gross_margin_prior: float | None = None
    asset_turnover: float | None = None
    asset_turnover_prior: float | None = None

    ebit: float | None = None
    enterprise_value: float | None = None
    net_working_capital: float | None = None
    net_fixed_assets: float | None = None
    earnings_yield: float | None = None
    return_on_capital: float | None = None
    average_traded_value: float | None = None
    price_to_earnings: float | None = None

    return_1m: float | None = None
    return_12m: float | None = None
    daily_return: float | None = None

    net_foreign_inflow: float | None = None
    foreign_buy_value: float | None = None
    foreign_sell_value: float | None = None
    volume: float | None = None

    return_on_equity: float | None = None
    net_interest_margin: float | None = None
    non_performing_loans: float | None = None

    adapter_notes: list[str] = Field(default_factory=list)


class MethodResult(BaseModel):
    method: str
    version: str
    score: float | None = None
    breakdown: dict[str, Any] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    applicable: bool = True
    notes: list[str] = Field(default_factory=list)


class ComponentScores(BaseModel):
    quality: float | None = None
    value: float | None = None
    momentum: float | None = None
    flow: float | None = None


class CompositeResult(BaseModel):
    symbol: str
    score: float | None = None
    rank: int | None = None
    components: ComponentScores
    methods: dict[str, MethodResult]
    coverage: float = Field(ge=0, le=1)
    excluded_reason: str | None = None
    notes: list[str] = Field(default_factory=list)
    weights_used: dict[str, float] = Field(default_factory=dict)


class ScoresResponse(BaseModel):
    results: list[CompositeResult]
    weights: Weights
    universe_size: int
    ranked_count: int
    disclaimer: str = "Information and analysis only. Not investment advice."
