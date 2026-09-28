from collections.abc import Sequence

from app.services.scoring.base import method_result
from app.services.scoring.config import METHOD_VERSION, MIN_PIOTROSKI_TESTS
from app.services.scoring.types import MethodResult, StockInputs

TEST_SPECS = (
    ("roa_positive", "ROA > 0", "roa"),
    ("cfo_positive", "cash flow from operations > 0", "cash_flow_from_operations"),
    ("roa_increased", "ROA higher than last year", "roa_prior"),
    ("accrual", "cash flow from operations > net income", "net_income"),
    ("leverage_decreased", "long-term debt ratio lower than last year", "long_term_debt_ratio_prior"),
    ("current_ratio_increased", "current ratio higher than last year", "current_ratio_prior"),
    ("no_new_shares", "no new shares issued", "shares_outstanding_prior"),
    ("gross_margin_increased", "gross margin higher than last year", "gross_margin_prior"),
    ("asset_turnover_increased", "asset turnover higher than last year", "asset_turnover_prior"),
)


class PiotroskiMethod:
    name = "piotroski"
    version = METHOD_VERSION
    required_fields = (
        "roa",
        "roa_prior",
        "cash_flow_from_operations",
        "net_income",
        "long_term_debt_ratio",
        "long_term_debt_ratio_prior",
        "current_ratio",
        "current_ratio_prior",
        "shares_outstanding",
        "shares_outstanding_prior",
        "gross_margin",
        "gross_margin_prior",
        "asset_turnover",
        "asset_turnover_prior",
    )

    def applies_to(self, stock: StockInputs) -> bool:
        return not stock.is_financial

    def score(self, stock: StockInputs, universe: Sequence[StockInputs]) -> MethodResult:
        del universe
        if not self.applies_to(stock):
            return method_result(
                method=self.name,
                version=self.version,
                applicable=False,
                reasons=["Piotroski F-Score is not applicable to financials."],
            )

        tests = _evaluate_tests(stock)
        computable = [test for test in tests if test["result"] != "unknown"]
        passes = [test for test in tests if test["result"] == "pass"]
        missing_fields = _missing_fields(stock)
        breakdown = {test["key"]: test for test in tests}
        breakdown["tests_computable"] = len(computable)
        breakdown["tests_passed"] = len(passes)

        if len(computable) < MIN_PIOTROSKI_TESTS:
            return method_result(
                method=self.name,
                version=self.version,
                score=None,
                breakdown=breakdown,
                reasons=[
                    f"Fewer than {MIN_PIOTROSKI_TESTS} tests are computable "
                    f"({len(computable)} of 9)."
                ]
                + [f"{test['label']}: {test['result']}" for test in tests],
                missing_fields=missing_fields,
            )

        f_score = len(passes)
        breakdown["f_score"] = f_score
        return method_result(
            method=self.name,
            version=self.version,
            score=float(f_score),
            breakdown=breakdown,
            reasons=[f"F-Score {f_score} of 9."]
            + [f"{test['label']}: {test['result']}" for test in tests],
            missing_fields=missing_fields,
        )


def _evaluate_tests(stock: StockInputs) -> list[dict]:
    outcomes = {
        "roa_positive": _truth(stock.roa is not None, lambda: stock.roa > 0),
        "cfo_positive": _truth(
            stock.cash_flow_from_operations is not None,
            lambda: stock.cash_flow_from_operations > 0,
        ),
        "roa_increased": _truth(
            stock.roa is not None and stock.roa_prior is not None,
            lambda: stock.roa > stock.roa_prior,
        ),
        "accrual": _truth(
            stock.cash_flow_from_operations is not None and stock.net_income is not None,
            lambda: stock.cash_flow_from_operations > stock.net_income,
        ),
        "leverage_decreased": _truth(
            stock.long_term_debt_ratio is not None
            and stock.long_term_debt_ratio_prior is not None,
            lambda: stock.long_term_debt_ratio < stock.long_term_debt_ratio_prior,
        ),
        "current_ratio_increased": _truth(
            stock.current_ratio is not None and stock.current_ratio_prior is not None,
            lambda: stock.current_ratio > stock.current_ratio_prior,
        ),
        "no_new_shares": _truth(
            stock.shares_outstanding is not None
            and stock.shares_outstanding_prior is not None,
            lambda: stock.shares_outstanding <= stock.shares_outstanding_prior,
        ),
        "gross_margin_increased": _truth(
            stock.gross_margin is not None and stock.gross_margin_prior is not None,
            lambda: stock.gross_margin > stock.gross_margin_prior,
        ),
        "asset_turnover_increased": _truth(
            stock.asset_turnover is not None and stock.asset_turnover_prior is not None,
            lambda: stock.asset_turnover > stock.asset_turnover_prior,
        ),
    }

    tests = []
    for key, label, _field in TEST_SPECS:
        result = outcomes[key]
        tests.append(
            {
                "key": key,
                "label": label,
                "result": "unknown" if result is None else ("pass" if result else "fail"),
            }
        )
    return tests


def _truth(computable: bool, predicate) -> bool | None:
    if not computable:
        return None
    return bool(predicate())


def _missing_fields(stock: StockInputs) -> list[str]:
    missing = []
    for field_name in PiotroskiMethod.required_fields:
        if getattr(stock, field_name) is None:
            missing.append(field_name)
    return missing
