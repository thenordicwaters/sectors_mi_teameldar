"""Unusual-activity detection. Pure math on cached numbers, 0 Sectors credits."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from app.models.anomalies import AnomalyFlag, AnomalyKind

# Volume: per-symbol standard score against that symbol's own trailing baseline.
VOLUME_STANDARD_SCORE_THRESHOLD = 3.0
MIN_VOLUME_BASELINE_SESSIONS = 30

# Foreign flow: the cache holds one Sectors trading day, so there is no per-symbol series
# to score against and this is cross-sectional instead. Net flow over *foreign turnover*
# is trapped in -1..1 and can never reach 3 deviations; net flow over normal traded value
# is unbounded, so that is the measured quantity. The cross-section is fat-tailed rather
# than normal, and 3.0 flagged one name in nine on the 18 Sept snapshot; 8.0 keeps the
# tab to flows worth several normal trading days (about 30 names).
FOREIGN_FLOW_STANDARD_SCORE_THRESHOLD = 8.0
MIN_AVERAGE_TRADED_VALUE = 100_000_000  # Rp 100 million, same floor the score uses
MIN_ABSOLUTE_NET_FOREIGN_INFLOW = 1_000_000_000  # Rp 1 billion
MIN_FOREIGN_FLOW_CROSS_SECTION = 30

# A normal distribution's median absolute deviation is sigma / 1.4826.
MAD_TO_STANDARD_DEVIATION = 1.4826

METHOD_NOTES = [
    "Volume: standard score of the latest session against that symbol's own "
    f"trailing baseline (Yahoo OHLCV overlay, at least {MIN_VOLUME_BASELINE_SESSIONS} "
    "sessions, latest session excluded from the baseline). Flagged at "
    f"{VOLUME_STANDARD_SCORE_THRESHOLD:.1f} standard deviations.",
    "Foreign flow: robust standard score (median and median absolute deviation) of net "
    "foreign inflow divided by the stock's 20-session average traded value, across the "
    "IDX cross-section on the latest cached Sectors foreign-flow day. Flagged at "
    f"{FOREIGN_FLOW_STANDARD_SCORE_THRESHOLD:.1f} standard deviations with net flow of "
    f"at least Rp {MIN_ABSOLUTE_NET_FOREIGN_INFLOW:,.0f}. The cache holds one trading "
    "day, so this compares a stock with the market that day, not with its own history.",
]


@dataclass
class AnomalyInput:
    """One cached stock. Volume comes from the Yahoo overlay, flow from Sectors."""

    symbol: str
    company_name: str
    volume: float | None = None
    volume_average: float | None = None
    volume_standard_deviation: float | None = None
    volume_baseline_sessions: int | None = None
    volume_as_of_date: str | None = None
    average_traded_value: float | None = None
    net_foreign_inflow: float | None = None
    flow_as_of_date: str | None = None


def detect_unusual_activity(
    stocks: list[AnomalyInput],
) -> dict[str, list[AnomalyFlag]]:
    """Flags keyed by symbol. A symbol with nothing unusual is absent from the result."""
    cross_section = _foreign_flow_cross_section(stocks)
    flags: dict[str, list[AnomalyFlag]] = {}
    for stock in stocks:
        for flag in (
            _volume_flag(stock),
            _foreign_flow_flag(stock, cross_section),
        ):
            if flag is not None:
                flags.setdefault(stock.symbol, []).append(flag)
    return flags


def _volume_flag(stock: AnomalyInput) -> AnomalyFlag | None:
    if stock.volume is None or stock.volume_average is None:
        return None
    if stock.volume_standard_deviation is None or stock.volume_standard_deviation <= 0:
        return None
    sessions = stock.volume_baseline_sessions or 0
    if sessions < MIN_VOLUME_BASELINE_SESSIONS:
        return None
    standard_score = (stock.volume - stock.volume_average) / stock.volume_standard_deviation
    if abs(standard_score) < VOLUME_STANDARD_SCORE_THRESHOLD:
        return None
    direction = "above" if standard_score > 0 else "below"
    multiple_text = ""
    if stock.volume_average > 0:
        multiple_text = f", about {stock.volume / stock.volume_average:.1f}x normal"
    return AnomalyFlag(
        ticker_symbol=stock.symbol,
        company_name=stock.company_name,
        anomaly_kind=AnomalyKind.volume_standard_score,
        label="Volume spike" if standard_score > 0 else "Volume drought",
        standard_score=round(standard_score, 2),
        observed_value=stock.volume,
        baseline_value=stock.volume_average,
        threshold=VOLUME_STANDARD_SCORE_THRESHOLD,
        as_of_date=stock.volume_as_of_date or "",
        reason=(
            f"Volume {_share_count_text(stock.volume)} is {abs(standard_score):.1f} "
            f"standard deviations {direction} its {sessions}-session average of "
            f"{_share_count_text(stock.volume_average)}{multiple_text} "
            f"(Yahoo OHLCV overlay, {stock.volume_as_of_date or 'latest session'})."
        ),
    )


@dataclass
class _ForeignFlowCrossSection:
    median_multiple: float
    scale: float
    sample_size: int
    as_of_date: str


def _foreign_flow_cross_section(
    stocks: list[AnomalyInput],
) -> _ForeignFlowCrossSection | None:
    multiples = []
    as_of_dates = set()
    for stock in stocks:
        multiple = _flow_multiple(stock)
        if multiple is None:
            continue
        multiples.append(multiple)
        if stock.flow_as_of_date:
            as_of_dates.add(stock.flow_as_of_date)
    if len(multiples) < MIN_FOREIGN_FLOW_CROSS_SECTION:
        return None
    median_multiple = median(multiples)
    median_absolute_deviation = median(
        [abs(value - median_multiple) for value in multiples]
    )
    # A zero deviation means more than half the cross-section had identical flow. Nothing
    # can be unusual against that, so no flow flags rather than a divide by zero.
    if median_absolute_deviation <= 0:
        return None
    scale = median_absolute_deviation * MAD_TO_STANDARD_DEVIATION
    return _ForeignFlowCrossSection(
        median_multiple=median_multiple,
        scale=scale,
        sample_size=len(multiples),
        as_of_date=max(as_of_dates) if as_of_dates else "",
    )


def _foreign_flow_flag(
    stock: AnomalyInput,
    cross_section: _ForeignFlowCrossSection | None,
) -> AnomalyFlag | None:
    if cross_section is None:
        return None
    multiple = _flow_multiple(stock)
    if multiple is None or stock.net_foreign_inflow is None:
        return None
    if abs(stock.net_foreign_inflow) < MIN_ABSOLUTE_NET_FOREIGN_INFLOW:
        return None
    standard_score = (multiple - cross_section.median_multiple) / cross_section.scale
    if abs(standard_score) < FOREIGN_FLOW_STANDARD_SCORE_THRESHOLD:
        return None
    side = "net buyers" if stock.net_foreign_inflow > 0 else "net sellers"
    direction = "above" if standard_score > 0 else "below"
    return AnomalyFlag(
        ticker_symbol=stock.symbol,
        company_name=stock.company_name,
        anomaly_kind=AnomalyKind.foreign_flow_standard_score,
        label=(
            "Foreign inflow spike" if standard_score > 0 else "Foreign outflow spike"
        ),
        standard_score=round(standard_score, 2),
        observed_value=multiple,
        baseline_value=cross_section.median_multiple,
        threshold=FOREIGN_FLOW_STANDARD_SCORE_THRESHOLD,
        as_of_date=stock.flow_as_of_date or cross_section.as_of_date,
        reason=(
            f"Foreign investors were {side} of "
            f"{_rupiah_text(abs(stock.net_foreign_inflow))} on "
            f"{stock.flow_as_of_date or cross_section.as_of_date}, "
            f"{abs(multiple):.1f}x this stock's 20-session average traded value: "
            f"{abs(standard_score):.1f} robust standard deviations {direction} the IDX "
            f"median across {cross_section.sample_size} tickers that day "
            "(Sectors foreign flow over Yahoo traded value, cross-sectional)."
        ),
    )


def _flow_multiple(stock: AnomalyInput) -> float | None:
    """Net foreign inflow as a multiple of the stock's normal daily traded value, so a
    small cap and a blue chip sit on the same axis."""
    if stock.net_foreign_inflow is None:
        return None
    if stock.average_traded_value is None:
        return None
    if stock.average_traded_value < MIN_AVERAGE_TRADED_VALUE:
        return None
    return stock.net_foreign_inflow / stock.average_traded_value


def _share_count_text(volume: float) -> str:
    absolute = abs(volume)
    if absolute >= 1_000_000_000:
        return f"{volume / 1_000_000_000:.1f}B shares"
    if absolute >= 1_000_000:
        return f"{volume / 1_000_000:.1f}M shares"
    if absolute >= 1_000:
        return f"{volume / 1_000:.1f}k shares"
    return f"{volume:,.0f} shares"


def _rupiah_text(value: float) -> str:
    absolute = abs(value)
    if absolute >= 1_000_000_000_000:
        return f"Rp {value / 1_000_000_000_000:.1f}T"
    if absolute >= 1_000_000_000:
        return f"Rp {value / 1_000_000_000:.1f}B"
    if absolute >= 1_000_000:
        return f"Rp {value / 1_000_000:.1f}M"
    return f"Rp {value:,.0f}"
