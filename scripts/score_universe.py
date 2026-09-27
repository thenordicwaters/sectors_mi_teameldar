#!/usr/bin/env python3
"""Print top 10 and bottom 10 composite scores from the SQLite cache. Zero Sectors credits."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.scoring.adapters.sectors import load_universe_inputs  # noqa: E402
from app.services.scoring.service import ScoringService  # noqa: E402


def _line(result) -> str:
    components = result.components
    return (
        f"{result.rank or '-':>4}  {result.symbol:<10}  "
        f"score={result.score if result.score is not None else 'None':>8}  "
        f"Q={_fmt(components.quality)}  "
        f"V={_fmt(components.value)}  "
        f"M={_fmt(components.momentum)}  "
        f"F={_fmt(components.flow)}  "
        f"cov={result.coverage:.2f}  "
        f"{result.excluded_reason or ''}"
    )


def _fmt(value: float | None) -> str:
    if value is None:
        return "  None"
    return f"{value:6.1f}"


def main() -> int:
    stocks = load_universe_inputs()
    if not stocks:
        print("No cached universe. Run: python -m app.sectors.snapshot")
        return 1
    results = ScoringService().score_universe(stocks)
    ranked = sorted(
        [result for result in results if result.score is not None],
        key=lambda result: (result.rank or 0, result.symbol),
    )
    unranked_count = len(results) - len(ranked)
    print(f"Universe {len(results)} | ranked {len(ranked)} | unranked {unranked_count}")
    print("Information and analysis only. Not investment advice.")
    print("\nTOP 10")
    for result in ranked[:10]:
        print(_line(result))
        piotroski = result.methods.get("piotroski")
        magic = result.methods.get("magic_formula")
        momentum = result.methods.get("momentum")
        if piotroski and piotroski.breakdown:
            print(f"     Piotroski: {piotroski.reasons[0] if piotroski.reasons else piotroski.score}")
        if magic and magic.breakdown:
            print(
                "     Magic Formula: "
                f"EY={magic.breakdown.get('earnings_yield')} "
                f"ROC={magic.breakdown.get('return_on_capital')} "
                f"ranks={magic.breakdown.get('earnings_yield_rank')}/"
                f"{magic.breakdown.get('return_on_capital_rank')}"
            )
        if momentum and momentum.breakdown:
            print(
                "     Momentum: "
                f"source={momentum.breakdown.get('source')} "
                f"value={momentum.breakdown.get('ranked_value')}"
            )
    print("\nBOTTOM 10")
    for result in ranked[-10:]:
        print(_line(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
