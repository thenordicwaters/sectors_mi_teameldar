from __future__ import annotations

from app.models.anomalies import AnomalyFlag, AnomalyKind, UnusualActivityResponse
from app.models.common import Pagination, ScoreBreakdown, ViewTab
from app.models.screener import ScreenerResponse, ScreenerRow
from app.sectors.database import get_database
from app.services.anomalies import METHOD_NOTES, AnomalyInput, detect_unusual_activity
from app.services.scoring.service import ScoringService
from app.services.scoring.adapters.sectors import load_universe_inputs
from app.services.scoring.types import CompositeResult
from app.services.signals import badges_for_stock

SORTABLE_ROW_FIELDS = {
    "overall_score": "overall_score",
    "market_capitalization": "market_capitalization",
    "ticker_symbol": "ticker_symbol",
    "daily_close_change": "daily_close_change",
    "last_close_price": "last_close_price",
    "net_foreign_inflow": "net_foreign_inflow",
    "price_to_earnings_trailing_twelve_months": (
        "price_to_earnings_trailing_twelve_months"
    ),
}

_derived_rows: list[ScreenerRow] | None = None
_derived_stamp: tuple | None = None
_scoring_service = ScoringService()


def invalidate_derived_cache() -> None:
    global _derived_rows, _derived_stamp
    _derived_rows = None
    _derived_stamp = None


def list_screener_page(
    *,
    sort_by: str,
    page_size: int,
    page_offset: int,
    view_tab: ViewTab,
    signal_filter: str | None = None,
    anomaly_only: bool = False,
) -> ScreenerResponse:
    rows = list(_derived_screener_rows())
    if signal_filter:
        rows = [
            row
            for row in rows
            if any(badge.signal_kind.value == signal_filter for badge in row.signals)
        ]
    if anomaly_only:
        rows = [row for row in rows if row.has_anomaly]
    rows = _sort_rows(rows, sort_by)
    total_count = len(rows)
    page = rows[page_offset : page_offset + page_size]
    return ScreenerResponse(
        results=page,
        view_tab=view_tab,
        pagination=_pagination(total_count, len(page), page_size, page_offset),
    )


def list_unusual_activity_page(
    *,
    anomaly_kind: str | None,
    min_standard_score: float,
    page_size: int,
    page_offset: int,
) -> UnusualActivityResponse:
    """Serve flags derived from the cache only. Does not call Sectors (0 credits)."""
    flags = [flag for row in _derived_screener_rows() for flag in row.anomalies]
    if anomaly_kind:
        flags = [flag for flag in flags if flag.anomaly_kind.value == anomaly_kind]
    flags = [flag for flag in flags if abs(flag.standard_score) >= min_standard_score]
    flags.sort(
        key=lambda flag: (-abs(flag.standard_score), flag.ticker_symbol)
    )
    total_count = len(flags)
    page = flags[page_offset : page_offset + page_size]
    return UnusualActivityResponse(
        results=page,
        pagination=_pagination(total_count, len(page), page_size, page_offset),
        method_notes=list(METHOD_NOTES),
    )


def get_screener_row(ticker_symbol: str) -> ScreenerRow | None:
    normalized = ticker_symbol.strip().upper()
    if not normalized.endswith(".JK"):
        normalized = f"{normalized}.JK"
    for row in _derived_screener_rows():
        if row.ticker_symbol == normalized:
            return row
    return None


def screener_row_from_sectors_payload(sectors_row: dict) -> ScreenerRow | None:
    """A live Sectors row that is not in the snapshot: no Score, no badges, no flags."""
    from app.sectors.snapshot import materialize_company_row

    columns = materialize_company_row(sectors_row)
    if columns is None:
        return None
    return _to_screener_row(columns, score=None, signals=[], anomalies=[], volume=None)


def _derived_screener_rows() -> list[ScreenerRow]:
    global _derived_rows, _derived_stamp
    stamp = _database_stamp()
    if _derived_rows is not None and _derived_stamp == stamp:
        return _derived_rows
    _derived_rows = _build_derived_rows()
    _derived_stamp = stamp
    return _derived_rows


def _database_stamp() -> tuple:
    from app.config import settings

    database_path = settings.resolved_sqlite_path()
    modified_times = []
    for candidate in (
        database_path,
        database_path.with_name(database_path.name + "-wal"),
        database_path.with_name(database_path.name + "-shm"),
    ):
        if candidate.exists():
            modified_times.append(candidate.stat().st_mtime)
    database = get_database()
    meta_rows = database.execute(
        """
        SELECT snapshot_name, completed_at, row_count
        FROM snapshot_meta
        ORDER BY snapshot_name
        """
    ).fetchall()
    counts = database.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM company_universe) AS companies,
            (SELECT COUNT(*) FROM fifty_two_week_high_flags) AS week_highs,
            (SELECT COUNT(*) FROM insider_filings) AS filings,
            (SELECT COUNT(*) FROM yahoo_price_overlay) AS overlays,
            (SELECT COUNT(*) FROM foreign_flow) AS flows
        """
    ).fetchone()
    return (
        str(database_path),
        max(modified_times) if modified_times else 0.0,
        tuple(
            (row["snapshot_name"], row["completed_at"], row["row_count"])
            for row in meta_rows
        ),
        int(counts["companies"]),
        int(counts["week_highs"]),
        int(counts["filings"]),
        int(counts["overlays"]),
        int(counts["flows"]),
    )


def _build_derived_rows() -> list[ScreenerRow]:
    database = get_database()
    company_rows = [
        dict(row)
        for row in database.execute(
            """
            SELECT
                company_universe.*,
                latest_foreign_flow.net_foreign_inflow AS net_foreign_inflow,
                latest_foreign_flow.foreign_buy_value_rupiah AS foreign_buy_value_rupiah,
                latest_foreign_flow.foreign_sell_value_rupiah AS foreign_sell_value_rupiah,
                latest_foreign_flow.trading_date AS trading_date
            FROM company_universe
            LEFT JOIN (
                SELECT ticker_symbol, net_foreign_inflow,
                       foreign_buy_value_rupiah, foreign_sell_value_rupiah,
                       trading_date
                FROM foreign_flow
                WHERE trading_date = (SELECT MAX(trading_date) FROM foreign_flow)
            ) AS latest_foreign_flow
                ON latest_foreign_flow.ticker_symbol = company_universe.ticker_symbol
            """
        ).fetchall()
    ]
    if not company_rows:
        return []

    stocks = load_universe_inputs()
    scores = {
        result.symbol: result
        for result in _scoring_service.score_universe(stocks)
    }
    week_highs = {
        row["ticker_symbol"]
        for row in database.execute(
            "SELECT ticker_symbol FROM fifty_two_week_high_flags"
        ).fetchall()
    }
    overlays = {
        row["ticker_symbol"]: dict(row)
        for row in database.execute("SELECT * FROM yahoo_price_overlay").fetchall()
    }
    insider_buys = _latest_insider_buys()
    anomalies = detect_unusual_activity(
        [_to_anomaly_input(row, overlays.get(row["ticker_symbol"]) or {}) for row in company_rows]
    )
    derived = []
    for row in company_rows:
        symbol = row["ticker_symbol"]
        overlay = overlays.get(symbol) or {}
        score = scores.get(symbol)
        derived.append(
            _to_screener_row(
                row,
                score=score,
                anomalies=anomalies.get(symbol, []),
                signals=badges_for_stock(
                    symbol=symbol,
                    daily_close_change=row.get("daily_close_change"),
                    last_close_price=row.get("last_close_price"),
                    is_sectors_52w_high=symbol in week_highs,
                    high_52w=overlay.get("high_52w"),
                    net_foreign_inflow=row.get("net_foreign_inflow"),
                    foreign_buy_value=row.get("foreign_buy_value_rupiah"),
                    foreign_sell_value=row.get("foreign_sell_value_rupiah"),
                    insider_buy=insider_buys.get(symbol),
                ),
                volume=overlay.get("volume"),
            )
        )
    return derived


def _to_anomaly_input(row: dict, overlay: dict) -> AnomalyInput:
    return AnomalyInput(
        symbol=row["ticker_symbol"],
        company_name=row["company_name"],
        volume=overlay.get("volume"),
        volume_average=overlay.get("volume_average"),
        volume_standard_deviation=overlay.get("volume_standard_deviation"),
        volume_baseline_sessions=overlay.get("volume_baseline_sessions"),
        volume_as_of_date=overlay.get("as_of_date"),
        average_traded_value=overlay.get("average_traded_value"),
        net_foreign_inflow=row.get("net_foreign_inflow"),
        flow_as_of_date=row.get("trading_date"),
    )


def _latest_insider_buys() -> dict[str, dict]:
    rows = get_database().execute(
        """
        SELECT ticker_symbol, filed_at, holder_name, amount_transaction
        FROM insider_filings
        WHERE lower(transaction_type) = 'buy'
        ORDER BY filed_at DESC
        """
    ).fetchall()
    latest: dict[str, dict] = {}
    for row in rows:
        symbol = row["ticker_symbol"]
        if symbol not in latest:
            latest[symbol] = dict(row)
    return latest


def _to_screener_row(
    row: dict,
    *,
    score: CompositeResult | None,
    signals: list,
    anomalies: list[AnomalyFlag],
    volume: float | None,
) -> ScreenerRow:
    breakdown = ScoreBreakdown(
        overall_score=score.score if score is not None else None,
        value_score=score.components.value if score is not None else None,
        quality_score=score.components.quality if score is not None else None,
        momentum_score=score.components.momentum if score is not None else None,
        flow_score=score.components.flow if score is not None else None,
        universe_rank=score.rank if score is not None else row.get("market_capitalization_rank"),
    )
    return ScreenerRow(
        ticker_symbol=row["ticker_symbol"],
        company_name=row["company_name"],
        sector=row.get("sector"),
        sub_sector=row.get("sub_sector"),
        last_close_price=row.get("last_close_price"),
        daily_close_change=row.get("daily_close_change"),
        market_capitalization=row.get("market_capitalization"),
        price_to_earnings_trailing_twelve_months=row.get(
            "price_to_earnings_trailing_twelve_months"
        ),
        price_to_book_most_recent_quarter=row.get(
            "price_to_book_most_recent_quarter"
        ),
        price_to_sales_trailing_twelve_months=row.get(
            "price_to_sales_trailing_twelve_months"
        ),
        return_on_equity_trailing_twelve_months=row.get(
            "return_on_equity_trailing_twelve_months"
        ),
        dividend_yield_trailing_twelve_months=row.get(
            "dividend_yield_trailing_twelve_months"
        ),
        net_foreign_inflow=row.get("net_foreign_inflow"),
        volume=volume,
        score=breakdown,
        signals=signals,
        has_anomaly=bool(anomalies),
        anomalies=anomalies,
    )


def _sort_rows(rows: list[ScreenerRow], sort_by: str) -> list[ScreenerRow]:
    descending = sort_by.startswith("-")
    field_name = sort_by[1:] if descending else sort_by
    attribute_name = SORTABLE_ROW_FIELDS.get(field_name, "market_capitalization")
    if field_name not in SORTABLE_ROW_FIELDS:
        descending = True

    def raw_value(row: ScreenerRow):
        if attribute_name == "overall_score":
            return row.score.overall_score
        return getattr(row, attribute_name)

    present = [row for row in rows if raw_value(row) is not None]
    missing = [row for row in rows if raw_value(row) is None]
    present.sort(key=lambda row: (raw_value(row), row.ticker_symbol), reverse=descending)
    missing.sort(key=lambda row: row.ticker_symbol)
    return present + missing


def _pagination(
    total_count: int,
    shown_count: int,
    page_size: int,
    page_offset: int,
) -> Pagination:
    has_next_page = page_offset + shown_count < total_count
    has_previous_page = page_offset > 0
    return Pagination(
        total_count=total_count,
        shown_count=shown_count,
        page_size=page_size,
        page_offset=page_offset,
        has_next_page=has_next_page,
        has_previous_page=has_previous_page,
        next_page_offset=page_offset + page_size if has_next_page else None,
        previous_page_offset=(
            None if not has_previous_page else max(page_offset - page_size, 0)
        ),
    )
