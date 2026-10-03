import sqlite3
import threading
from pathlib import Path

from app.config import settings

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS http_cache (
        cache_key TEXT PRIMARY KEY,
        method TEXT NOT NULL,
        path TEXT NOT NULL,
        query_json TEXT NOT NULL,
        status_code INTEGER NOT NULL,
        response_json TEXT NOT NULL,
        credits_charged INTEGER NOT NULL,
        fetched_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS credit_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT,
        logged_at TEXT NOT NULL,
        path TEXT NOT NULL,
        status_code INTEGER NOT NULL,
        credits_charged INTEGER NOT NULL,
        cache_hit INTEGER NOT NULL,
        credits_used_after INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS snapshot_meta (
        snapshot_name TEXT PRIMARY KEY,
        completed_at TEXT NOT NULL,
        row_count INTEGER NOT NULL,
        credits_used INTEGER NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS company_universe (
        ticker_symbol TEXT PRIMARY KEY,
        company_name TEXT NOT NULL,
        sector TEXT,
        sub_sector TEXT,
        listing_board TEXT,
        last_close_price REAL,
        daily_close_change REAL,
        market_capitalization REAL,
        market_capitalization_rank INTEGER,
        price_to_earnings_trailing_twelve_months REAL,
        price_to_book_most_recent_quarter REAL,
        price_to_sales_trailing_twelve_months REAL,
        return_on_equity_trailing_twelve_months REAL,
        dividend_yield_trailing_twelve_months REAL,
        query_values_json TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS foreign_flow (
        ticker_symbol TEXT NOT NULL,
        trading_date TEXT NOT NULL,
        net_foreign_inflow INTEGER,
        foreign_buy_value_rupiah INTEGER,
        foreign_sell_value_rupiah INTEGER,
        PRIMARY KEY (ticker_symbol, trading_date)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS yahoo_price_overlay (
        ticker_symbol TEXT PRIMARY KEY,
        return_1m REAL,
        return_12m REAL,
        volume REAL,
        average_traded_value REAL,
        volume_average REAL,
        volume_standard_deviation REAL,
        volume_baseline_sessions INTEGER,
        trading_days INTEGER,
        last_close REAL,
        high_52w REAL,
        as_of_date TEXT,
        notes TEXT,
        fetched_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fifty_two_week_high_flags (
        ticker_symbol TEXT PRIMARY KEY,
        last_close_price REAL,
        fetched_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS insider_filings (
        filing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticker_symbol TEXT NOT NULL,
        filed_at TEXT,
        holder_name TEXT,
        holder_type TEXT,
        transaction_type TEXT,
        amount_transaction INTEGER,
        transaction_value REAL,
        title TEXT,
        source_url TEXT
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS insider_filings_symbol_idx
    ON insider_filings (ticker_symbol, filed_at)
    """,
    """
    CREATE TABLE IF NOT EXISTS market_quote_cache (
        cache_key TEXT PRIMARY KEY,
        payload_json TEXT NOT NULL,
        fetched_at TEXT NOT NULL
    )
    """,
]


class Database:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._lock = threading.Lock()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(
            database_path,
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        for statement in SCHEMA_STATEMENTS:
            self._connection.execute(statement)
        _ensure_column(self._connection, "yahoo_price_overlay", "high_52w", "REAL")
        _ensure_column(self._connection, "yahoo_price_overlay", "volume_average", "REAL")
        _ensure_column(
            self._connection,
            "yahoo_price_overlay",
            "volume_standard_deviation",
            "REAL",
        )
        _ensure_column(
            self._connection,
            "yahoo_price_overlay",
            "volume_baseline_sessions",
            "INTEGER",
        )
        self._connection.commit()

    def execute(
        self,
        statement: str,
        parameters: tuple | dict = (),
    ) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._connection.execute(statement, parameters)
            self._connection.commit()
            return cursor

    def execute_many(
        self,
        statement: str,
        sequence_of_parameters: list[tuple],
    ) -> None:
        with self._lock:
            self._connection.executemany(statement, sequence_of_parameters)
            self._connection.commit()

    def close(self) -> None:
        with self._lock:
            self._connection.close()


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, column_type: str) -> None:
    existing = {
        row[1]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        )


_database: Database | None = None


def get_database() -> Database:
    global _database
    database_path = settings.resolved_sqlite_path()
    if _database is None or _database.database_path != database_path:
        _database = Database(database_path)
    return _database


def reset_database() -> None:
    global _database
    if _database is not None:
        _database.close()
    _database = None
    try:
        from app.sectors.repository import invalidate_derived_cache

        invalidate_derived_cache()
    except ImportError:
        pass
