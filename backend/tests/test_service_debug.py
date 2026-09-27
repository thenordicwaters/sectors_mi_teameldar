from app.services.scoring.service import ScoringService
from tests.scoring_factory import complete_piotroski, synthetic_stock


def test_score_universe_ranks_and_sorts_excluded_last():
    strong = complete_piotroski("STRONG.JK", passing=True)
    weak = complete_piotroski("WEAK.JK", passing=False).model_copy(
        update={
            "earnings_yield": 0.01,
            "return_on_capital": 0.02,
            "daily_return": -0.03,
            "net_foreign_inflow": -2_000_000,
        }
    )
    suspended = synthetic_stock("SUSP.JK", is_suspended=True)

    results = ScoringService().score_universe([suspended, weak, strong])

    assert [result.symbol for result in results] == ["STRONG.JK", "WEAK.JK", "SUSP.JK"]
    assert [result.rank for result in results] == [1, 2, None]
    assert results[0].score > results[1].score
    assert results[2].excluded_reason == "Suspended."
    assert set(results[0].methods) == {
        "piotroski",
        "magic_formula",
        "momentum",
        "foreign_flow",
        "financials_quality",
    }
