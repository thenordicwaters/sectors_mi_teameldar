from app.services.scoring.service import ScoringService
from tests.scoring_factory import synthetic_stock


def test_score_universe_debug():
    universe = [
        synthetic_stock("AAA.JK", return_12m=0.50, return_1m=0.05),
        synthetic_stock("BBB.JK", return_12m=0.10, return_1m=0.00),
        synthetic_stock("CCC.JK", return_12m=-0.20, return_1m=-0.05),
    ]
    service = ScoringService()

    breakpoint()
    results = service.score_universe(universe)

    assert len(results) == 3
    assert {r.symbol for r in results} == {"AAA.JK", "BBB.JK", "CCC.JK"}
