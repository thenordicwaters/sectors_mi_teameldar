"""Validation for the Sectors structured screener `where` clause.

Field names, operators and bracket notation come from the documented screener
reference: https://docs.sectors.app/api-references/v2/indonesia/screener/companies

Everything here runs locally, before any live call. A clause we can reject ourselves
costs 0 credits and can explain itself; a clause we pass through costs 1 credit per page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from difflib import get_close_matches

MAX_CLAUSE_LENGTH = 400
MAX_CONDITIONS = 10
EARLIEST_YEAR = 1990

OPERATORS = ("=", "!=", ">", ">=", "<", "<=", "like", "in")
LOGIC_KEYWORDS = ("and", "or")
_RESERVED_WORDS = frozenset({*LOGIC_KEYWORDS, "like", "in", "not", "null", "true", "false"})

DIRECT_FIELDS = frozenset(
    {
        "symbol",
        "company_name",
        "listing_board",
        "industry",
        "sub_industry",
        "sector",
        "sub_sector",
        "market_cap",
        "market_cap_rank",
        "employee_num",
        "employee_num_rank",
        "listing_date",
        "last_ex_dividend_date",
        "last_close_price",
        "daily_close_change",
        "forward_pe",
        "intrinsic_value",
        "esg_score",
        "yield_ttm",
        "dividend_ttm",
        "payout_ratio",
        "cash_payout_ratio",
        "yoy_quarter_earnings_growth",
        "yoy_quarter_revenue_growth",
    }
)

ARRAY_FIELDS = frozenset({"tags", "indices", "affiliates"})

LATEST_VALUE_FIELDS = frozenset(
    {
        "pe_ttm",
        "pb_mrq",
        "ps_ttm",
        "dar_mrq",
        "der_mrq",
        "roa_ttm",
        "roe_ttm",
        "total_assets_mrq",
        "total_equity_mrq",
        "total_revenue_mrq",
        "earnings_mrq",
        "total_liabilities_mrq",
        "yearly_mcap_change",
        "dividend_yield_avg_period",
        "dividend_yield_avg",
        "ytd_low_price",
        "ytd_low_date",
        "ytd_high_price",
        "ytd_high_date",
        "52_w_low_price",
        "52_w_low_date",
        "52_w_high_price",
        "52_w_high_date",
        "90_d_low_price",
        "90_d_low_date",
        "90_d_high_price",
        "90_d_high_date",
        "all_time_low_price",
        "all_time_low_date",
        "all_time_high_price",
        "all_time_high_date",
    }
)

YEARLY_FIELDS = frozenset(
    {
        "eps",
        "eps_growth",
        "total_dividend",
        "total_yield",
        "earnings",
        "allowance_for_loans",
        "capital_expenditure",
        "cash_and_equivalents",
        "cash_inflow",
        "cash_only",
        "cash_outflow",
        "core_capital_tier1",
        "cost_of_revenue",
        "credit_rwa",
        "current_account",
        "current_assets",
        "current_liabilities",
        "earnings_before_tax",
        "ebit",
        "ebitda",
        "end_cash_position",
        "financing_cash_flow",
        "fixed_assets",
        "free_cash_flow",
        "gross_loan",
        "gross_profit",
        "high_quality_liquid_asset",
        "interest_expense",
        "interest_expense_non_operating",
        "interest_income",
        "inventories",
        "investing_cash_flow",
        "market_rwa",
        "net_cash_flow",
        "net_interest_income",
        "net_loan",
        "net_premium_income",
        "non_current_liabilities",
        "non_interest_bearing_liabilities",
        "non_interest_income",
        "non_loan_assets",
        "non_loan_earning_assets",
        "non_loan_non_earning_assets",
        "non_operating_income_or_loss",
        "operating_cash_flow",
        "operating_expense",
        "operating_pnl",
        "operational_rwa",
        "other_interest_bearing_liabilities",
        "outstanding_shares",
        "prepaid_assets",
        "premium_expense",
        "premium_income",
        "provision",
        "realized_capital_goods_investment",
        "retained_earnings",
        "revenue",
        "savings_account",
        "supplementary_capital_tier2",
        "tax",
        "time_deposit",
        "total_assets",
        "total_capital",
        "total_cash_and_due_from_banks",
        "total_debt",
        "total_deposit",
        "total_equity",
        "total_liabilities",
        "total_risk_weighted_asset",
        "special_mention_loan",
        "non_performing_loan",
        "restructured_loan_current",
        "forecast_eps_growth",
        "forecast_revenue_growth",
        "forecast_eps_estimate",
        "forecast_revenue_estimate",
        "pe",
        "pb",
        "ps",
        "pcf",
        "peg",
        "enterprise_to_ebitda",
        "enterprise_to_revenue",
        "pb_peer_avg",
        "pe_peer_avg",
        "ps_peer_avg",
        "debt_to_asset_ratio",
        "debt_to_equity_ratio",
        "cash_flow_to_debt_ratio",
        "interest_coverage_ratio",
        "current_ratio",
        "operating_cash_flow_margin",
        "fixed_asset_turnover",
        "total_asset_turnover",
        "roa",
        "roe",
        "net_profit_margin",
        "gross_profit_margin",
        "operating_profit_margin",
        "capital_adequacy_ratio",
        "casa_ratio",
        "leverage_ratio",
        "loan_to_deposit_ratio",
        "liquidity_coverage_ratio",
        "efficiency_ratio",
        "net_interest_margin",
        "cost_to_income_ratio",
    }
)

QUARTERLY_FIELDS = frozenset(
    {
        "revenue_q",
        "earnings_q",
        "net_loan_q",
        "gross_profit_q",
        "time_deposit_q",
        "operating_pnl_q",
        "total_deposit_q",
        "ebit_q",
        "ebitda_q",
        "earnings_before_tax_q",
        "tax_q",
        "cost_of_revenue_q",
        "current_account_q",
        "interest_income_q",
        "premium_expense_q",
        "savings_account_q",
        "interest_expense_q",
        "operating_expense_q",
        "non_operating_income_or_loss_q",
        "interest_expense_non_operating_q",
        "non_interest_bearing_liabilities_q",
        "realized_capital_goods_investment_q",
        "other_interest_bearing_liabilities_q",
        "total_assets_q",
        "current_assets_q",
        "total_liabilities_q",
        "net_premium_income_q",
        "allowance_for_loans_q",
        "current_liabilities_q",
        "non_current_liabilities_q",
        "total_equity_q",
        "total_debt_q",
        "cash_only_q",
        "provision_q",
        "gross_loan_q",
        "total_cash_and_due_from_banks_q",
        "operating_cash_flow_q",
        "investing_cash_flow_q",
        "financing_cash_flow_q",
        "net_interest_income_q",
        "non_interest_income_q",
        "free_cash_flow_q",
        "premium_income_q",
        "capital_expenditure_q",
    }
)

LIST_OBJECT_FIELDS = frozenset(
    {
        "key_executives_name",
        "key_executives_position",
        "executives_shareholdings_name",
        "executives_shareholdings_share_amount",
        "executives_shareholdings_share_percentage",
        "major_shareholders_name",
        "major_shareholders_share_value",
        "major_shareholders_share_amount",
        "major_shareholders_share_percentage",
        "free_float",
    }
)

PLAIN_FIELDS = DIRECT_FIELDS | ARRAY_FIELDS | LATEST_VALUE_FIELDS | LIST_OBJECT_FIELDS
ALL_FIELDS = PLAIN_FIELDS | YEARLY_FIELDS | QUARTERLY_FIELDS

EXAMPLE_CLAUSES = (
    "market_cap > 10000000000000 and pe_ttm < 15",
    "sector = 'Financials' and roe_ttm > 0.15",
    "tags in ['52-w-high'] and yield_ttm > 0.03",
    "revenue[2024] > revenue[2023] * 1.2",
    "roe[2024] > 0.15 and der_mrq < 1",
)

_LITERAL_PLACEHOLDER = "@"
_STRING_LITERAL = re.compile(r"'[^']*'|\"[^\"]*\"")
_ALLOWED_SKELETON_CHARACTERS = re.compile(r"^[A-Za-z0-9_@\[\]\(\),\.\s\+\-\*/<>=!]*$")
_TOKEN = re.compile(r"[A-Za-z0-9_]+(\[[^\[\]]*\])?")
_COMPARISON = re.compile(r"(!=|>=|<=|=|>|<)|\b(like|in)\b", re.IGNORECASE)
_YEAR_BRACKET = re.compile(r"^\d{4}$")
_QUARTER_BRACKET = re.compile(r"^Q[1-4]-\d{4}$", re.IGNORECASE)
_ORDER_BY_TOKEN = re.compile(r"^-?([A-Za-z0-9_]+)(\[[^\[\]]*\])?$")


class WhereClauseError(ValueError):
    """Rejected before any Sectors call, so it costs 0 credits."""

    def __init__(self, message: str, suggestions: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.suggestions = suggestions or []


@dataclass
class ValidatedWhereClause:
    clause: str
    fields: tuple[str, ...]
    condition_count: int


def validate_where_clause(clause: str) -> ValidatedWhereClause:
    """Return the clause ready to send, or raise WhereClauseError explaining why not."""
    trimmed = " ".join((clause or "").split())
    if not trimmed:
        raise WhereClauseError("A where clause is required, for example market_cap > 1000000000000.")
    if len(trimmed) > MAX_CLAUSE_LENGTH:
        raise WhereClauseError(
            f"Where clause is {len(trimmed)} characters; the limit is {MAX_CLAUSE_LENGTH}."
        )

    skeleton = _STRING_LITERAL.sub(_LITERAL_PLACEHOLDER, trimmed)
    for quote in ("'", '"'):
        if quote in skeleton:
            raise WhereClauseError(f"Unbalanced {quote} quote in the where clause.")
    if not _ALLOWED_SKELETON_CHARACTERS.match(skeleton):
        raise WhereClauseError(
            "Where clause contains characters the screener does not accept. "
            "Allowed outside quotes: field names, numbers, () [] , . + - * / "
            "and the operators = != > >= < <=."
        )
    _assert_balanced(skeleton)

    condition_count = len(_COMPARISON.findall(skeleton))
    if condition_count == 0:
        raise WhereClauseError(
            "Where clause has no comparison. Use one of: " + ", ".join(OPERATORS) + "."
        )
    if condition_count > MAX_CONDITIONS:
        raise WhereClauseError(
            f"Where clause has {condition_count} comparisons; the limit is {MAX_CONDITIONS}."
        )

    fields: list[str] = []
    for match in _TOKEN.finditer(skeleton):
        token = match.group(0)
        base = token.split("[", 1)[0]
        bracket = (match.group(1) or "").strip("[]")
        if base.lower() in _RESERVED_WORDS:
            continue
        if not bracket and _is_number(base):
            continue
        fields.append(_validate_field(base, bracket))
    if not fields:
        raise WhereClauseError(
            "Where clause references no screener field. "
            "See GET /api/screener/custom/fields for the list."
        )
    return ValidatedWhereClause(
        clause=trimmed,
        fields=tuple(dict.fromkeys(fields)),
        condition_count=condition_count,
    )


def validate_order_by(order_by: str) -> str:
    """One field, optionally prefixed with - for descending. Arithmetic is not accepted."""
    trimmed = (order_by or "").strip()
    if not trimmed:
        raise WhereClauseError("order_by is required, for example -market_cap.")
    match = _ORDER_BY_TOKEN.match(trimmed)
    if match is None:
        raise WhereClauseError(
            f"order_by {trimmed!r} must be a single field name, optionally prefixed with -."
        )
    base = match.group(1)
    bracket = (match.group(2) or "").strip("[]")
    if _is_number(base) and not bracket:
        raise WhereClauseError("order_by must be a field name, not a number.")
    _validate_field(base, bracket)
    return trimmed


def _validate_field(base: str, bracket: str) -> str:
    name = base.lower()
    if name in YEARLY_FIELDS:
        if not bracket:
            raise WhereClauseError(
                f"{base} is a yearly field: write {base}[2024]."
            )
        if not _YEAR_BRACKET.match(bracket):
            raise WhereClauseError(
                f"{base}[{bracket}] must use a four-digit year, for example {base}[2024]."
            )
        year = int(bracket)
        if not EARLIEST_YEAR <= year <= date.today().year + 5:
            raise WhereClauseError(
                f"{base}[{bracket}] is outside {EARLIEST_YEAR}-{date.today().year + 5}."
            )
        return f"{name}[{bracket}]"
    if name in QUARTERLY_FIELDS:
        if not bracket:
            raise WhereClauseError(
                f"{base} is a quarterly field: write {base}[Q1-2024]."
            )
        if not _QUARTER_BRACKET.match(bracket):
            raise WhereClauseError(
                f"{base}[{bracket}] must use quarter notation, for example {base}[Q1-2024]."
            )
        return f"{name}[{bracket.upper()}]"
    if name in PLAIN_FIELDS:
        if bracket:
            raise WhereClauseError(
                f"{base} does not take bracket notation; drop [{bracket}]."
            )
        return name
    raise WhereClauseError(
        f"{base} is not a Sectors screener field.",
        suggestions=get_close_matches(name, sorted(ALL_FIELDS), n=3, cutoff=0.6),
    )


def _assert_balanced(skeleton: str) -> None:
    stack: list[str] = []
    pairs = {")": "(", "]": "["}
    for character in skeleton:
        if character in "([":
            stack.append(character)
        elif character in pairs:
            if not stack or stack.pop() != pairs[character]:
                raise WhereClauseError(f"Unbalanced {character} in the where clause.")
    if stack:
        raise WhereClauseError(f"Unclosed {stack[-1]} in the where clause.")


def _is_number(token: str) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True
