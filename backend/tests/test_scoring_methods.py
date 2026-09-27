from app.services.scoring.methods.financials_quality import FinancialsQualityMethod
from app.services.scoring.methods.foreign_flow import ForeignFlowMethod
from app.services.scoring.methods.magic_formula import MagicFormulaMethod
from app.services.scoring.methods.momentum import MomentumMethod
from app.services.scoring.methods.piotroski import PiotroskiMethod
from tests.scoring_factory import complete_piotroski, synthetic_stock


def test_piotroski_all_pass() -> None:
    stock = complete_piotroski("PASS.JK", passing=True)
    result = PiotroskiMethod().score(stock, [stock])
    assert result.applicable is True
    assert result.score == 9
    assert result.breakdown["tests_passed"] == 9
    assert all(
        result.breakdown[key]["result"] == "pass"
        for key in (
            "roa_positive",
            "cfo_positive",
            "roa_increased",
            "accrual",
            "leverage_decreased",
            "current_ratio_increased",
            "no_new_shares",
            "gross_margin_increased",
            "asset_turnover_increased",
        )
    )


def test_piotroski_all_fail() -> None:
    stock = complete_piotroski("FAIL.JK", passing=False)
    result = PiotroskiMethod().score(stock, [stock])
    assert result.score == 0
    assert result.breakdown["tests_passed"] == 0


def test_piotroski_missing_data_scores_none() -> None:
    stock = synthetic_stock("MISS.JK", roa=0.05)
    result = PiotroskiMethod().score(stock, [stock])
    assert result.score is None
    assert "roa_prior" in result.missing_fields
    assert result.breakdown["tests_computable"] < 6
    assert result.breakdown["roa_positive"]["result"] == "pass"


def test_piotroski_not_applicable_to_financials() -> None:
    stock = complete_piotroski("BANK.JK", passing=True)
    stock.is_financial = True
    result = PiotroskiMethod().score(stock, [stock])
    assert result.applicable is False
    assert result.score is None


def test_magic_formula_ranks_both_legs() -> None:
    cheap = synthetic_stock("CHEP.JK", earnings_yield=0.20, return_on_capital=0.30)
    expensive = synthetic_stock("EXPN.JK", earnings_yield=0.05, return_on_capital=0.05)
    universe = [cheap, expensive]
    method = MagicFormulaMethod()
    cheap_result = method.score(cheap, universe)
    expensive_result = method.score(expensive, universe)
    assert cheap_result.score == 100.0
    assert expensive_result.score == 0.0
    assert cheap_result.breakdown["earnings_yield_rank"] == 1
    assert cheap_result.breakdown["return_on_capital_rank"] == 1


def test_magic_formula_negative_ebit_ranks_worst() -> None:
    loss = synthetic_stock("LOSS.JK", earnings_yield=-0.10, return_on_capital=0.40)
    profit = synthetic_stock("GAIN.JK", earnings_yield=0.05, return_on_capital=0.10)
    method = MagicFormulaMethod()
    universe = [loss, profit]
    assert method.score(loss, universe).breakdown["earnings_yield_rank"] > method.score(
        profit, universe
    ).breakdown["earnings_yield_rank"]


def test_magic_formula_excludes_financials_and_missing() -> None:
    bank = synthetic_stock("BANK.JK", is_financial=True, sector="Financials")
    empty = synthetic_stock("NONE.JK", earnings_yield=None, return_on_capital=None)
    method = MagicFormulaMethod()
    assert method.applies_to(bank) is False
    assert method.score(bank, [bank]).applicable is False
    missing = method.score(empty, [empty])
    assert missing.score is None
    assert "earnings_yield" in missing.missing_fields


def test_momentum_twelve_minus_one() -> None:
    stock = synthetic_stock(
        "MOM1.JK",
        return_12m=0.21,
        return_1m=0.10,
        daily_return=0.50,
    )
    peer = synthetic_stock("MOM2.JK", return_12m=0.0, return_1m=0.0, daily_return=0.0)
    result = MomentumMethod().score(stock, [stock, peer])
    assert result.breakdown["source"] == "twelve_minus_one"
    assert abs(result.breakdown["twelve_minus_one"] - 0.1) < 1e-9
    assert result.score == 100.0


def test_momentum_missing_history_is_none() -> None:
    stock = synthetic_stock(
        "NEW.JK",
        return_12m=None,
        return_1m=None,
        daily_return=None,
    )
    result = MomentumMethod().score(stock, [stock])
    assert result.score is None
    assert result.applicable is False
    assert "return_12m" in result.missing_fields


def test_foreign_flow_pass_and_missing() -> None:
    buyer = synthetic_stock(
        "BUY.JK",
        net_foreign_inflow=50,
        foreign_buy_value=80,
        foreign_sell_value=30,
    )
    seller = synthetic_stock(
        "SEL.JK",
        net_foreign_inflow=-20,
        foreign_buy_value=10,
        foreign_sell_value=30,
    )
    method = ForeignFlowMethod()
    buy_result = method.score(buyer, [buyer, seller])
    sell_result = method.score(seller, [buyer, seller])
    assert buy_result.score > sell_result.score
    missing = synthetic_stock(
        "NOFL.JK",
        net_foreign_inflow=None,
        foreign_buy_value=None,
        foreign_sell_value=None,
    )
    missing_result = method.score(missing, [buyer, missing])
    assert missing_result.score is None
    assert missing_result.applicable is False
    assert "net_foreign_inflow" in missing_result.missing_fields


def test_financials_quality_within_financials_only() -> None:
    strong = synthetic_stock(
        "BNKA.JK",
        is_financial=True,
        sector="Financials",
        return_on_equity=0.20,
        net_interest_margin=0.06,
        non_performing_loans=0.01,
    )
    weak = synthetic_stock(
        "BNKB.JK",
        is_financial=True,
        sector="Financials",
        return_on_equity=0.05,
        net_interest_margin=0.02,
        non_performing_loans=0.08,
    )
    industrial = synthetic_stock("INDS.JK", is_financial=False)
    method = FinancialsQualityMethod()
    assert method.applies_to(industrial) is False
    strong_result = method.score(strong, [strong, weak, industrial])
    weak_result = method.score(weak, [strong, weak, industrial])
    assert strong_result.score == 100.0
    assert weak_result.score == 0.0
    missing = synthetic_stock(
        "BNKC.JK",
        is_financial=True,
        return_on_equity=None,
        net_interest_margin=None,
        non_performing_loans=None,
    )
    missing_result = method.score(missing, [missing])
    assert missing_result.score is None
    assert "return_on_equity" in missing_result.missing_fields
