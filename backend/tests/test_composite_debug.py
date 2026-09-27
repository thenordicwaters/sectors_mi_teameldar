from app.services.scoring.base import method_result
from app.services.scoring.methods.composite import CompositeMethod
from app.services.scoring.types import Weights
from tests.scoring_factory import synthetic_stock


def test_combine_weights_parts_and_excludes_thin_coverage():
    full = synthetic_stock("FULL.JK")
    thin = synthetic_stock("THIN.JK")
    stocks = [full, thin]
    method_results = {
        "FULL.JK": {
            "piotroski": method_result(method="piotroski", version="1", score=9.0),
            "magic_formula": method_result(method="magic_formula", version="1", score=80.0),
            "momentum": method_result(method="momentum", version="1", score=60.0),
            "foreign_flow": method_result(method="foreign_flow", version="1", score=40.0),
        },
        "THIN.JK": {
            "piotroski": method_result(method="piotroski", version="1", score=0.0),
            "magic_formula": method_result(method="magic_formula", version="1", score=20.0),
            "momentum": method_result(method="momentum", version="1", applicable=False),
            "foreign_flow": method_result(method="foreign_flow", version="1", applicable=False),
        },
    }

    results = CompositeMethod().combine(
        stocks, method_results, Weights(quality=30, value=25, momentum=25, flow=20)
    )
    by_symbol = {result.symbol: result for result in results}

    full_result = by_symbol["FULL.JK"]
    assert full_result.components.quality == 100
    assert full_result.components.value == 100
    assert full_result.score == 78
    assert full_result.rank == 1
    assert full_result.coverage == 1

    thin_result = by_symbol["THIN.JK"]
    assert thin_result.score is None
    assert thin_result.rank is None
    assert thin_result.coverage == 0.5
    assert thin_result.excluded_reason.startswith("Fewer than 3 score parts")
