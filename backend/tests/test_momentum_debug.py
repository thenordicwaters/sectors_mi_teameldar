from app.services.scoring.methods.momentum import MomentumMethod
from tests.scoring_factory import synthetic_stock


def test_momentum_ranks_twelve_minus_one():
    universe = [
        synthetic_stock("AAA.JK", return_12m=0.50, return_1m=0.05),
        synthetic_stock("BBB.JK", return_12m=0.10, return_1m=0.00),
        synthetic_stock("CCC.JK", return_12m=-0.20, return_1m=-0.05),
    ]
    method = MomentumMethod()

    breakpoint()
    result = method.score(universe[0], universe)

    assert result.applicable is True
    assert result.breakdown["source"] == "twelve_minus_one"
    assert result.score == 100
