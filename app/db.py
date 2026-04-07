from __future__ import annotations

from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings


def create_engine_and_session_factory(
    settings: Settings,
) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    engine_kwargs = {
        "future": True,
        "echo": settings.debug,
        "pool_pre_ping": True,
        "connect_args": {
            "statement_cache_size": settings.db_statement_cache_size,
        },
    }

    if settings.db_use_null_pool:
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["pool_size"] = settings.db_pool_size
        engine_kwargs["max_overflow"] = settings.db_max_overflow
        engine_kwargs["pool_timeout"] = settings.db_pool_timeout
        engine_kwargs["pool_recycle"] = settings.db_pool_recycle

    engine = create_async_engine(settings.database_url, **engine_kwargs)
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, session_factory
