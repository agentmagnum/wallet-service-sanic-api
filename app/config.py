from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_host: str
    app_port: int
    app_workers: int
    debug: bool
    database_url: str
    db_pool_size: int
    db_max_overflow: int
    db_pool_timeout: int
    db_pool_recycle: int
    db_use_null_pool: bool
    db_statement_cache_size: int
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    payment_secret_key: str
    login_rate_limit_requests: int
    login_rate_limit_window_seconds: int
    webhook_rate_limit_requests: int
    webhook_rate_limit_window_seconds: int


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "wallet-service"),
        app_host=os.getenv("APP_HOST", "0.0.0.0"),
        app_port=int(os.getenv("APP_PORT", "8000")),
        app_workers=max(1, int(os.getenv("APP_WORKERS", "1"))),
        debug=_as_bool(os.getenv("DEBUG"), default=False),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/wallet_service",
        ),
        db_pool_size=max(1, int(os.getenv("DB_POOL_SIZE", "10"))),
        db_max_overflow=max(0, int(os.getenv("DB_MAX_OVERFLOW", "5"))),
        db_pool_timeout=max(1, int(os.getenv("DB_POOL_TIMEOUT", "30"))),
        db_pool_recycle=max(1, int(os.getenv("DB_POOL_RECYCLE", "1800"))),
        db_use_null_pool=_as_bool(os.getenv("DB_USE_NULL_POOL"), default=False),
        db_statement_cache_size=max(0, int(os.getenv("DB_STATEMENT_CACHE_SIZE", "100"))),
        jwt_secret=os.getenv("JWT_SECRET", "change-me-jwt-secret-32-bytes-min"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "60")),
        payment_secret_key=os.getenv("PAYMENT_SECRET_KEY", "change-me-payment-secret"),
        login_rate_limit_requests=max(0, int(os.getenv("LOGIN_RATE_LIMIT_REQUESTS", "30"))),
        login_rate_limit_window_seconds=max(1, int(os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", "60"))),
        webhook_rate_limit_requests=max(0, int(os.getenv("WEBHOOK_RATE_LIMIT_REQUESTS", "300"))),
        webhook_rate_limit_window_seconds=max(1, int(os.getenv("WEBHOOK_RATE_LIMIT_WINDOW_SECONDS", "60"))),
    )
