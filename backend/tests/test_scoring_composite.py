from app.services.scoring.config import DEFAULT_WEIGHTS, MIN_COMPOSITE_PARTS
from app.services.scoring.service import ScoringService
from app.services.scoring.types import Weights
from tests.scoring_factory import complete_piotroski, synthetic_stock


def test_composite_reweights_missing_quality() -> None:
    stock = synthetic_stock(
        "REWT.JK",
        earnings_yield=0.20,
        return_on_capital=0.20,
        daily_return=0.02,
        net_foreign_inflow=50,
        foreign_buy_value=80,
        foreign_sell_value=30,
    )
    results = ScoringService().score_universe([stock])
    result = results[0]
    assert result.components.quality is None
    assert result.components.value is not None
    assert result.components.momentum is not None
    assert result.components.flow is not None
    assert result.score is not None
    used = result.weights_used
    assert "quality" not in used
    assert abs(sum(used.values()) - 100) < 1e-6
    expected = (
        result.components.value * DEFAULT_WEIGHTS.value
        + result.components.momentum * DEFAULT_WEIGHTS.momentum
        + result.components.flow * DEFAULT_WEIGHTS.flow
    ) / (
        DEFAULT_WEIGHTS.value + DEFAULT_WEIGHTS.momentum + DEFAULT_WEIGHTS.flow
    )
    assert abs(result.score - round(expected, 4)) < 1e-6


def test_composite_unranked_with_fewer_than_three_parts() -> None:
    stock = synthetic_stock(
        "THIN.JK",
        earnings_yield=None,
        return_on_capital=None,
        ebit=None,
        daily_return=0.01,
        net_foreign_inflow=None,
        foreign_buy_value=None,
        foreign_sell_value=None,
    )
    result = ScoringService().score_universe([stock])[0]
    available = [
        score
        for score in result.components.model_dump().values()
        if score is not None
    ]
    assert len(available) < MIN_COMPOSITE_PARTS
    assert result.score is None
    assert result.rank is None
    assert result.excluded_reason is not None
    assert "Fewer than 3" in result.excluded_reason


def test_composite_value_ranks_within_sector_when_peers_exist() -> None:
    sector_a = [
        synthetic_stock(
            f"A{index:03d}.JK",
            sector="Energy",
            earnings_yield=0.10 + index * 0.01,
            return_on_capital=0.10 + index * 0.01,
            daily_return=0.01,
        )
        for index in range(8)
    ]
    outsider = synthetic_stock(
        "B001.JK",
        sector="Healthcare",
        earnings_yield=0.50,
        return_on_capital=0.50,
        daily_return=0.01,
    )
    results = {
        result.symbol: result
        for result in ScoringService().score_universe(sector_a + [outsider])
    }
    assert results["A000.JK"].components.value == 0.0
    assert results["A007.JK"].components.value == 100.0
    assert results["B001.JK"].components.value == 100.0


def test_composite_weight_overrides_are_deterministic() -> None:
    stock = complete_piotroski("DET1.JK", passing=True)
    stock.daily_return = 0.02
    stock.earnings_yield = 0.12
    stock.return_on_capital = 0.18
    first = ScoringService().score_universe(
        [stock], Weights(quality=40, value=20, momentum=20, flow=20)
    )
    second = ScoringService().score_universe(
        [stock], Weights(quality=40, value=20, momentum=20, flow=20)
    )
    assert first[0].model_dump() == second[0].model_dump()
    assert first[0].components.quality == 100.0
