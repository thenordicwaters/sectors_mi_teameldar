"""Daily closes from Sectors, ending yesterday in Jakarta.

Each Sectors window costs 1 credit and is at most 90 days. A window that has
already ended is cached forever. The window that still ends on yesterday is a
new request on the next Jakarta date, which is the daily cache reset. Ranges
inside that latest window (1M and 3M) share it, so switching them does not
call Sectors again.

Yahoo Finance is used only when Sectors returns nothing for the latest window.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from app.sectors.client import SectorsClient, SectorsClientError, SectorsCreditBudgetError
from app.sectors.paths import (
    DAILY_CREDITS,
    DAILY_MAX_DAYS,
    DAILY_PATH_TEMPLATE,
    IHSG_EARLIEST,
    IHSG_INDEX_CODE,
    INDEX_DAILY_CREDITS,
    INDEX_DAILY_PATH_TEMPLATE,
)
from app.services.market_quotes import jakarta_today

logger = logging.getLogger("market.history")

PRICE_RANGES = ("1m", "3m", "1y", "all")
EPOCH = date.fromisoformat(IHSG_EARLIEST)
RANGE_LOOKBACK_DAYS = {"1m": 31, "3m": 90, "1y": 366}


def chart_as_of(today: date | None = None) -> date:
    """Last calendar day we are willing to show. Today is never included."""
    current = today or jakarta_today()
    return current - timedelta(days=1)


def windows_for_range(range_key: str, as_of: date) -> list[tuple[date, date]]:
    if range_key not in PRICE_RANGES:
        raise ValueError(range_key)
    if range_key == "all":
        span_start = EPOCH
    elif range_key == "1y":
        span_start = as_of - timedelta(days=365)
    else:
        span_start = as_of - timedelta(days=DAILY_MAX_DAYS - 1)
    span_start = max(_align_down(span_start), EPOCH)
    if span_start > as_of:
        span_start = as_of
    return _iter_windows(span_start, as_of)


def slice_bars(bars: list[dict], range_key: str, as_of: date) -> list[dict]:
    eligible = [bar for bar in bars if bar["date"] <= as_of.isoformat()]
    if not eligible:
        return []
    if range_key == "all":
        return eligible
    lookback = RANGE_LOOKBACK_DAYS[range_key]
    start = (as_of - timedelta(days=lookback - 1)).isoformat()
    return [bar for bar in eligible if bar["date"] >= start]


def load_index_history(
    range_key: str,
    *,
    today: date | None = None,
    client: SectorsClient | None = None,
) -> dict:
    return load_price_history(
        kind="index",
        symbol=IHSG_INDEX_CODE,
        name="IHSG",
        range_key=range_key,
        today=today,
        client=client,
    )


def load_price_history(
    *,
    kind: str,
    symbol: str,
    name: str,
    range_key: str,
    today: date | None = None,
    client: SectorsClient | None = None,
) -> dict:
    if range_key not in PRICE_RANGES:
        raise ValueError(range_key)
    as_of = chart_as_of(today)
    windows = windows_for_range(range_key, as_of)
    owns_client = client is None
    client = client or SectorsClient()
    source = "Sectors"
    try:
        try:
            bars = _fetch_sectors_windows(client, kind, symbol, windows)
        except SectorsCreditBudgetError:
            raise
        except SectorsClientError:
            logger.exception("sectors history failed for %s", symbol)
            bars = []
        if not _has_bar_on_or_before(bars, as_of):
            bars = _yahoo_bars(kind, symbol, windows[0][0], as_of)
            source = "Yahoo Finance"
        shown = slice_bars(bars, range_key, as_of)
        close, previous_close, change, session_date = _quote_from_bars(bars, as_of)
        logger.info(
            "history %s %s range=%s as_of=%s session=%s points=%s source=%s",
            kind,
            symbol,
            range_key,
            as_of.isoformat(),
            session_date,
            len(shown),
            source,
        )
        return {
            "symbol": "IHSG" if kind == "index" else f"{symbol}.JK",
            "name": name,
            "range": range_key,
            "as_of_date": as_of.isoformat(),
            "session_date": session_date,
            "close": close,
            "previous_close": previous_close,
            "change": change,
            "points": shown,
            "source": source,
        }
    finally:
        if owns_client:
            client.close()


def _fetch_sectors_windows(
    client: SectorsClient,
    kind: str,
    symbol: str,
    windows: list[tuple[date, date]],
) -> list[dict]:
    merged: dict[str, dict] = {}
    for start, end in windows:
        for bar in _fetch_sectors_window(client, kind, symbol, start, end):
            if start.isoformat() <= bar["date"] <= end.isoformat():
                merged[bar["date"]] = bar
    return [merged[key] for key in sorted(merged)]


def _fetch_sectors_window(
    client: SectorsClient,
    kind: str,
    symbol: str,
    start: date,
    end: date,
) -> list[dict]:
    if kind == "index":
        path = INDEX_DAILY_PATH_TEMPLATE.format(index_code=symbol)
        cost = INDEX_DAILY_CREDITS
        price_key = "price"
    else:
        path = DAILY_PATH_TEMPLATE.format(symbol=symbol)
        cost = DAILY_CREDITS
        price_key = "close"
    response = client.get(
        path,
        {"start": start.isoformat(), "end": end.isoformat()},
        success_credit_cost=cost,
    )
    if response.status_code != 200 or not isinstance(response.payload, list):
        raise SectorsClientError(f"{path} returned {response.status_code}")
    return _bars_from_payload(response.payload, price_key)


def _bars_from_payload(payload: list, price_key: str) -> list[dict]:
    bars: dict[str, dict] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_date = item.get("date")
        raw_price = item.get(price_key)
        if not isinstance(raw_date, str) or raw_price is None:
            continue
        try:
            close = float(raw_price)
        except (TypeError, ValueError):
            continue
        session_date = raw_date[:10]
        bars[session_date] = {"date": session_date, "close": close}
    return [bars[key] for key in sorted(bars)]


def _yahoo_bars(kind: str, symbol: str, start: date, end: date) -> list[dict]:
    import pandas as pd
    import yfinance as yf

    yahoo_symbol = "^JKSE" if kind == "index" else f"{symbol}.JK"
    try:
        frame = yf.download(
            yahoo_symbol,
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception:
        logger.exception("yahoo history failed for %s", yahoo_symbol)
        return []
    if frame is None or frame.empty:
        return []
    close = frame["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    bars = []
    for stamp, price in zip(close.index, close.to_numpy()):
        if pd.isna(price):
            continue
        session_date = pd.Timestamp(stamp).date().isoformat()
        if session_date > end.isoformat():
            continue
        bars.append({"date": session_date, "close": float(price)})
    bars.sort(key=lambda bar: bar["date"])
    return bars


def _quote_from_bars(
    bars: list[dict], as_of: date
) -> tuple[float | None, float | None, float | None, str | None]:
    eligible = [bar for bar in bars if bar["date"] <= as_of.isoformat()]
    if not eligible:
        return None, None, None, None
    last = eligible[-1]
    previous = eligible[-2]["close"] if len(eligible) > 1 else None
    change = None
    if previous not in (None, 0):
        change = last["close"] / previous - 1
    return last["close"], previous, change, last["date"]


def _has_bar_on_or_before(bars: list[dict], as_of: date) -> bool:
    limit = as_of.isoformat()
    return any(bar["date"] <= limit for bar in bars)


def _align_down(day: date) -> date:
    if day <= EPOCH:
        return EPOCH
    offset = (day - EPOCH).days
    block = (offset // DAILY_MAX_DAYS) * DAILY_MAX_DAYS
    return EPOCH + timedelta(days=block)


def _iter_windows(start: date, end: date) -> list[tuple[date, date]]:
    cursor = start
    windows: list[tuple[date, date]] = []
    while cursor <= end:
        block_end = cursor + timedelta(days=DAILY_MAX_DAYS - 1)
        window_end = min(block_end, end)
        windows.append((cursor, window_end))
        if window_end < block_end:
            break
        cursor = block_end + timedelta(days=1)
    return windows
