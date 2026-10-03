"""Latest traded prices from Yahoo Finance. Never calls Sectors, so the cost is 0 credits."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from app.sectors.credits import utc_now_iso
from app.sectors.database import get_database

logger = logging.getLogger("market.quotes")

JAKARTA = ZoneInfo("Asia/Jakarta")
QUOTE_TTL = timedelta(minutes=15)
IHSG_SYMBOL = "^JKSE"


@dataclass(frozen=True)
class DailyBar:
    close: float
    previous_close: float | None
    change: float | None
    session_date: str


def jakarta_today() -> date:
    return datetime.now(JAKARTA).date()


def classify_session(session_date: date, today: date) -> str:
    if session_date == today:
        return "today"
    if today.weekday() >= 5:
        return "weekend"
    return "earlier"


def download_daily(symbol: str) -> pd.DataFrame:
    import yfinance as yf

    return yf.download(
        symbol,
        period="10d",
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )


def download_intraday(symbol: str) -> pd.DataFrame:
    import yfinance as yf

    return yf.download(
        symbol,
        period="5d",
        interval="5m",
        auto_adjust=True,
        progress=False,
        threads=False,
    )


def daily_quote_from_frame(frame: pd.DataFrame) -> DailyBar | None:
    close = _close_series(frame)
    if close.empty:
        return None
    last_close = float(close.iloc[-1])
    previous_close = float(close.iloc[-2]) if len(close) > 1 else None
    change = None
    if previous_close not in (None, 0):
        change = last_close / previous_close - 1
    session_date = _session_date(close.index[-1])
    return DailyBar(
        close=last_close,
        previous_close=previous_close,
        change=change,
        session_date=session_date,
    )


def latest_intraday_session(frame: pd.DataFrame) -> tuple[str, list[dict[str, float | str]]] | None:
    close = _close_series(frame)
    if close.empty:
        return None
    local_dates = [_as_jakarta(stamp).date() for stamp in close.index]
    session = max(local_dates)
    points = []
    for stamp, price, local_date in zip(close.index, close.to_numpy(), local_dates):
        if local_date != session:
            continue
        points.append(
            {
                "time": _as_jakarta(stamp).isoformat(),
                "price": round(float(price), 2),
            }
        )
    if not points:
        return None
    return session.isoformat(), points


def previous_daily_close(frame: pd.DataFrame, session_date: str) -> float | None:
    prior = prior_daily_bar(frame, session_date)
    if prior is None:
        return None
    return prior["close"]


def prior_daily_bar(frame: pd.DataFrame | None, session_date: str) -> dict | None:
    """Last completed daily bar before `session_date`. Its high is the H-1 high."""
    if frame is None:
        return None
    chosen = None
    for bar in _daily_bars(frame):
        if bar["date"] < session_date:
            chosen = bar
    return chosen


def bar_on_date(frame: pd.DataFrame | None, session_date: str) -> dict | None:
    if frame is None:
        return None
    for bar in _daily_bars(frame):
        if bar["date"] == session_date:
            return bar
    return None


def session_view_from_frames(intraday: pd.DataFrame | None, daily: pd.DataFrame | None) -> dict | None:
    parsed = latest_intraday_session(intraday) if intraday is not None else None
    if parsed is None:
        bar = daily_quote_from_frame(daily) if daily is not None else None
        if bar is None:
            return None
        prior = prior_daily_bar(daily, bar.session_date)
        return {
            "close": bar.close,
            "previous_close": bar.previous_close,
            "change": bar.change,
            "session_date": bar.session_date,
            "prior_session_date": None if prior is None else prior["date"],
            "prior_high": None if prior is None else prior["high"],
            "points": [],
        }
    session_date, points = parsed
    official = bar_on_date(daily, session_date)
    prior = prior_daily_bar(daily, session_date)
    close = float(official["close"]) if official is not None else float(points[-1]["price"])
    previous_close = None if prior is None else prior["close"]
    change = None
    if previous_close not in (None, 0):
        change = close / previous_close - 1
    return {
        "close": close,
        "previous_close": previous_close,
        "change": change,
        "session_date": session_date,
        "prior_session_date": None if prior is None else prior["date"],
        "prior_high": None if prior is None else prior["high"],
        "points": points,
    }


def load_stock_quote(ticker_symbol: str, snapshot_close: float | None, snapshot_fetched_at: str | None) -> dict:
    cached = _read_fresh(f"session:{ticker_symbol}")
    live = cached
    if live is None:
        try:
            live = session_view_from_frames(
                download_intraday(ticker_symbol),
                download_daily(ticker_symbol),
            )
        except Exception:
            logger.exception("yahoo session failed for %s", ticker_symbol)
            live = None
        if live is None:
            live = _read_any(f"session:{ticker_symbol}")
        else:
            _write(f"session:{ticker_symbol}", live)
            logger.info(
                "yahoo session %s close=%s session=%s prior_high=%s points=%s",
                ticker_symbol,
                live.get("close"),
                live.get("session_date"),
                live.get("prior_high"),
                len(live.get("points") or []),
            )
    return _with_status(
        {
            "ticker_symbol": ticker_symbol,
            "close": None if not live else live.get("close"),
            "previous_close": None if not live else live.get("previous_close"),
            "change": None if not live else live.get("change"),
            "session_date": None if not live else live.get("session_date"),
            "snapshot_close": snapshot_close,
            "snapshot_fetched_at": snapshot_fetched_at,
            "prior_session_date": None if not live else live.get("prior_session_date"),
            "prior_high": None if not live else live.get("prior_high"),
            "points": [] if not live else live.get("points") or [],
            "source": "Yahoo Finance",
        }
    )


def load_ihsg_session() -> dict:
    cached = _read_fresh("ihsg:5m")
    live = cached
    if live is None:
        try:
            intraday = download_intraday(IHSG_SYMBOL)
            daily = download_daily(IHSG_SYMBOL)
            parsed = latest_intraday_session(intraday)
        except Exception:
            logger.exception("yahoo ihsg session failed")
            parsed = None
            daily = None
        if parsed is None:
            live = _read_any("ihsg:5m")
        else:
            session_date, points = parsed
            official = bar_on_date(daily, session_date)
            prior = prior_daily_bar(daily, session_date)
            last_price = float(official["close"]) if official is not None else float(points[-1]["price"])
            previous = None if prior is None else prior["close"]
            change = None
            if previous not in (None, 0):
                change = last_price / previous - 1
            live = {
                "session_date": session_date,
                "last_price": last_price,
                "previous_close": previous,
                "change": change,
                "prior_session_date": None if prior is None else prior["date"],
                "prior_high": None if prior is None else prior["high"],
                "points": points,
            }
            _write("ihsg:5m", live)
            logger.info("yahoo ihsg session=%s points=%s", session_date, len(points))
    return _with_status(
        {
            "symbol": IHSG_SYMBOL,
            "name": "IHSG",
            "session_date": None if not live else live.get("session_date"),
            "last_price": None if not live else live.get("last_price"),
            "previous_close": None if not live else live.get("previous_close"),
            "change": None if not live else live.get("change"),
            "prior_session_date": None if not live else live.get("prior_session_date"),
            "prior_high": None if not live else live.get("prior_high"),
            "points": [] if not live else live.get("points") or [],
            "source": "Yahoo Finance",
        }
    )


def _with_status(payload: dict) -> dict:
    session_date = payload.get("session_date")
    status = "unavailable"
    if isinstance(session_date, str) and session_date:
        status = classify_session(date.fromisoformat(session_date), jakarta_today())
    payload["session_status"] = status
    return payload


def _daily_bars(frame: pd.DataFrame) -> list[dict]:
    close = _field_series(frame, "Close")
    high = _field_series(frame, "High")
    bars = []
    for stamp, price in zip(close.index, close.to_numpy()):
        bars.append(
            {
                "date": _session_date(stamp),
                "close": float(price),
                "high": _value_at(high, stamp),
            }
        )
    return bars


def _value_at(series: pd.Series, stamp) -> float | None:
    if series.empty or stamp not in series.index:
        return None
    value = series.loc[stamp]
    if isinstance(value, pd.Series):
        value = value.iloc[0]
    if pd.isna(value):
        return None
    return float(value)


def _close_series(frame: pd.DataFrame | None) -> pd.Series:
    return _field_series(frame, "Close")


def _field_series(frame: pd.DataFrame | None, field: str) -> pd.Series:
    if frame is None or frame.empty:
        return pd.Series(dtype=float)
    if isinstance(frame.columns, pd.MultiIndex):
        if field in frame.columns.get_level_values(0):
            series = frame[field]
        elif field in frame.columns.get_level_values(-1):
            series = frame.xs(field, axis=1, level=-1)
        else:
            return pd.Series(dtype=float)
    elif field in frame.columns:
        series = frame[field]
    else:
        return pd.Series(dtype=float)
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    return series.dropna()


def _session_date(stamp) -> str:
    return _as_jakarta(stamp).date().isoformat()


def _as_jakarta(stamp) -> pd.Timestamp:
    parsed = pd.Timestamp(stamp)
    if parsed.tzinfo is None:
        return parsed
    return parsed.tz_convert(JAKARTA)


def _read_fresh(cache_key: str) -> dict | None:
    cached = _read_any(cache_key)
    if cached is None:
        return None
    fetched_at = cached.pop("_fetched_at", None)
    if not isinstance(fetched_at, str) or not _is_fresh(fetched_at):
        return None
    return cached


def _read_any(cache_key: str) -> dict | None:
    row = get_database().execute(
        "SELECT payload_json, fetched_at FROM market_quote_cache WHERE cache_key = ?",
        (cache_key,),
    ).fetchone()
    if row is None:
        return None
    payload = json.loads(row["payload_json"])
    if not isinstance(payload, dict):
        return None
    payload["_fetched_at"] = row["fetched_at"]
    return payload


def _write(cache_key: str, payload: dict) -> None:
    get_database().execute(
        """
        INSERT OR REPLACE INTO market_quote_cache (cache_key, payload_json, fetched_at)
        VALUES (?, ?, ?)
        """,
        (cache_key, json.dumps(payload), utc_now_iso()),
    )


def _is_fresh(fetched_at: str) -> bool:
    parsed = datetime.fromisoformat(fetched_at)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - parsed < QUOTE_TTL
