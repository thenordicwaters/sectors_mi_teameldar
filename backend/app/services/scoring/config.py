from app.services.scoring.types import Weights

METHOD_VERSION = "1.0.0"

DEFAULT_WEIGHTS = Weights(quality=30, value=25, momentum=25, flow=20)

# IDX Financials sector from the Phase 1 screener snapshot.
FINANCIAL_SECTORS = frozenset({"Financials"})
# IDX utilities sit under Infrastructures / Utilities in the snapshot.
UTILITY_SUB_SECTORS = frozenset({"Utilities"})
# Watchlist is special monitoring, not a suspension flag. Used as the illiquidity proxy.
ILLIQUID_LISTING_BOARDS = frozenset({"Watchlist"})

# Rupiah. Volume / average traded value is not in the cache, so this is the liquidity floor.
MIN_MARKET_CAP = 100_000_000_000
# Applied only when average_traded_value is present (Yahoo OHLCV overlay).
MIN_AVERAGE_TRADED_VALUE: float | None = 100_000_000

SECTOR_PEER_MINIMUM = 8
MIN_PIOTROSKI_TESTS = 6
MIN_COMPOSITE_PARTS = 3

FLOW_NET_RATIO_WEIGHT = 0.7
FLOW_RELATIVE_VOLUME_WEIGHT = 0.3
