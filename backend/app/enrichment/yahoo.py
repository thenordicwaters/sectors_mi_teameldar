from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.sectors.credits import utc_now_iso
from app.sectors.database import get_database

logger = logging.getLogger("enrichment.yahoo")

LOOKBACK_1M_SESSIONS = 21
LOOKBACK_12M_SESSIONS = 252
AVG_TRADED_SESSIONS = 20
DOWNLOAD_CHUNK_SIZE = 40
# Baseline for the volume standard score. The latest session is excluded so a spike
# cannot inflate the average it is measured against.
VOLUME_BASELINE_SESSIONS = 60

YAHOO_TO_STOCK_INPUTS = {
    "return_1m": "return_1m",
    "return_12m": "return_12m",
    "volume": "volume",
    "average_traded_value": "average_traded_value",
}


def load_yahoo_overlay_rows() -> dict[str, dict[str, Any]]:
    database = get_database()
    rows = database.execute("SELECT * FROM yahoo_price_overlay").fetchall()
    return {row["ticker_symbol"]: dict(row) for row in rows}


def apply_yahoo_overlay(stock, overlay: dict[str, Any] | None):
    """Fill empty StockInputs fields only. Never overwrite Sectors values."""
    if not overlay:
        return stock
    filled = []
    for yahoo_field, attribute_name in YAHOO_TO_STOCK_INPUTS.items():
        if getattr(stock, attribute_name) is None and overlay.get(yahoo_field) is not None:
            setattr(stock, attribute_name, overlay[yahoo_field])
            filled.append(attribute_name)
    if filled:
        stock.adapter_notes.append(
            "Yahoo Finance OHLCV overlay filled: " + ", ".join(filled) + "."
        )
    return stock


def enrich_symbols(
    symbols: list[str],
    *,
    force: bool = False,
    chunk_size: int = DOWNLOAD_CHUNK_SIZE,
) -> int:
    """Download 13 months of Yahoo OHLCV and cache derived metrics. 0 Sectors credits."""
    import yfinance as yf

    database = get_database()
    pending = list(symbols)
    if not force:
        existing = {
            row["ticker_symbol"]
            for row in database.execute(
                "SELECT ticker_symbol FROM yahoo_price_overlay"
            ).fetchall()
        }
        pending = [symbol for symbol in symbols if symbol not in existing]
    if not pending:
        logger.info("yahoo overlay already complete for %s symbols", len(symbols))
        return 0

    stored = 0
    for start in range(0, len(pending), chunk_size):
        chunk = pending[start : start + chunk_size]
        logger.info("yahoo download %s-%s / %s", start + 1, start + len(chunk), len(pending))
        frame = yf.download(
            chunk,
            period="13mo",
            auto_adjust=True,
            threads=False,
            progress=False,
            group_by="ticker",
        )
        rows = []
        for symbol in chunk:
            metrics = metrics_from_history(_frame_for_symbol(frame, symbol), symbol)
            if metrics is None:
                continue
            rows.append(
                (
                    symbol,
                    metrics.get("return_1m"),
                    metrics.get("return_12m"),
                    metrics.get("volume"),
                    metrics.get("average_traded_value"),
                    metrics.get("volume_average"),
                    metrics.get("volume_standard_deviation"),
                    metrics.get("volume_baseline_sessions"),
                    metrics.get("trading_days"),
                    metrics.get("last_close"),
                    metrics.get("high_52w"),
                    metrics.get("as_of_date"),
                    metrics.get("notes"),
                    utc_now_iso(),
                )
            )
        if rows:
            database.execute_many(
                """
                INSERT OR REPLACE INTO yahoo_price_overlay (
                    ticker_symbol, return_1m, return_12m, volume,
                    average_traded_value, volume_average,
                    volume_standard_deviation, volume_baseline_sessions,
                    trading_days, last_close, high_52w,
                    as_of_date, notes, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            stored += len(rows)
    database.execute(
        """
        INSERT OR REPLACE INTO snapshot_meta (snapshot_name, completed_at, row_count, credits_used)
        VALUES ('yahoo_price_overlay', ?, ?, 0)
        """,
        (utc_now_iso(), stored if force else len(pending)),
    )
    logger.info("yahoo overlay stored %s rows", stored)
    from app.sectors.repository import invalidate_derived_cache

    invalidate_derived_cache()
    return stored

def metrics_from_history(frame: pd.DataFrame | None, symbol: str) -> dict[str, Any] | None:
    if frame is None or frame.empty:
        return None
    if "Close" not in frame.columns:
        return None
    close = frame["Close"].dropna()
    if close.empty:
        return None
    volume = (
        frame["Volume"].reindex(close.index).fillna(0)
        if "Volume" in frame.columns
        else pd.Series(0, index=close.index)
    )

    last_close = float(close.iloc[-1])
    high_52w = None
    if "High" in frame.columns:
        high_window = frame["High"].reindex(close.index).dropna().tail(LOOKBACK_12M_SESSIONS)
        if not high_window.empty:
            high_52w = float(high_window.max())
    notes = []
    return_1m = None
    return_12m = None

    if len(close) > LOOKBACK_1M_SESSIONS:
        prior = float(close.iloc[-(LOOKBACK_1M_SESSIONS + 1)])
        if prior != 0:
            return_1m = last_close / prior - 1
    else:
        notes.append("Fewer than 21 sessions; 1-month return missing.")
    if len(close) > LOOKBACK_12M_SESSIONS:
        prior = float(close.iloc[-(LOOKBACK_12M_SESSIONS + 1)])
        if prior != 0:
            return_12m = last_close / prior - 1
    else:
        notes.append("Fewer than 12 months of Yahoo history; 12-1 not computed.")

    traded = close.astype(float) * volume.astype(float)
    average_traded_value = float(traded.tail(AVG_TRADED_SESSIONS).mean())
    baseline = volume.astype(float).iloc[:-1].tail(VOLUME_BASELINE_SESSIONS)
    volume_average = None
    volume_standard_deviation = None

    if len(baseline) >= 2:
        volume_average = float(baseline.mean())
        volume_standard_deviation = float(baseline.std(ddof=1))
    else:
        notes.append("Fewer than 3 sessions; volume baseline not computed.")
    return {
        "return_1m": return_1m,
        "return_12m": return_12m,
        "volume": float(volume.iloc[-1]),
        "average_traded_value": average_traded_value,
        "volume_average": volume_average,
        "volume_standard_deviation": volume_standard_deviation,
        "volume_baseline_sessions": int(len(baseline)),
        "trading_days": int(len(close)),
        "last_close": last_close,
        "high_52w": high_52w,
        "as_of_date": str(pd.Timestamp(close.index[-1]).date()),
        "notes": " ".join(notes) or None,
        "symbol": symbol,
    }

def _frame_for_symbol(data: pd.DataFrame, symbol: str) -> pd.DataFrame | None:
    if data is None or data.empty:
        return None
    if isinstance(data.columns, pd.MultiIndex):
        level_values = [str(value) for value in data.columns.get_level_values(0)]
        if symbol in data.columns.get_level_values(0):
            return data[symbol]
        if symbol in data.columns.get_level_values(-1):
            return data.xs(symbol, axis=1, level=-1)
        if not any(symbol == value for value in level_values):
            return None
    return data
