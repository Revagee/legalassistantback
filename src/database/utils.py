import os
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


@lru_cache
def get_async_engine(pool_size: int = 10, max_overflow: int = 5) -> AsyncEngine:
    engine = create_async_engine(
        url=os.getenv("DATABASE_URL", "").replace("postgres", "postgresql+asyncpg"),
        pool_size=pool_size,
        max_overflow=max_overflow,
    )

    return engine


@lru_cache
def get_session_factory() -> async_sessionmaker:
    """Get a session factory that can create independent database sessions.

    This is more efficient for connection pooling as each session can be created
    and closed independently, returning the connection to the pool.

    Returns:
        async_sessionmaker: A factory that creates AsyncSession objects
    """
    engine = get_async_engine()

    return async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        class_=AsyncSession,
    )


def get_session() -> AsyncSession:
    engine = get_async_engine()

    async_session_factory = async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    return async_session_factory()
