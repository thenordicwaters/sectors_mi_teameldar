from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        extra="ignore",
    )

    sectors_api_key: str = ""
    sectors_api_base_url: str = "https://api.sectors.app"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"
    sectors_sqlite_path: str = "data/sectors.db"
    sectors_credit_budget: int = 1000
    sectors_opening_credits_used: int = 0
    sectors_request_timeout_seconds: float = 30
    sectors_min_interval_seconds: float = 0.2

    def resolved_sqlite_path(self) -> Path:
        database_path = Path(self.sectors_sqlite_path)
        if database_path.is_absolute():
            return database_path
        backend_root = Path(__file__).resolve().parents[1]
        return backend_root / database_path


settings = Settings()
