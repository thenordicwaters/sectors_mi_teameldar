#!/usr/bin/env python3
"""Cache Yahoo Finance OHLCV overlays for the Sectors universe. 0 Sectors credits."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from app.enrichment.yahoo import enrich_symbols  # noqa: E402
from app.sectors.database import get_database  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fill 12-1 momentum and traded-value gaps from Yahoo Finance. "
            "Sectors stays the universe. 0 Sectors credits."
        )
    )
    parser.add_argument("--force", action="store_true", help="Re-download cached symbols.")
    parser.add_argument("--limit", type=int, default=None, help="Max symbols this run.")
    arguments = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    symbols = [
        row["ticker_symbol"]
        for row in get_database()
        .execute("SELECT ticker_symbol FROM company_universe ORDER BY ticker_symbol")
        .fetchall()
    ]
    if arguments.limit is not None:
        symbols = symbols[: arguments.limit]
    if not symbols:
        print("No cached universe. Run the Sectors snapshot first.")
        return 1
    stored = enrich_symbols(symbols, force=arguments.force)
    print(f"Yahoo overlay: {stored} symbols stored. Sectors credits this run: 0.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
