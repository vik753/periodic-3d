"""Async database access (SQLAlchemy 2 + asyncpg)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


class Database:
    """Engine and session factory. Creating it does not open a connection."""

    def __init__(self, url: str, *, pool_size: int = 5, max_overflow: int = 10) -> None:
        self.engine: AsyncEngine = create_async_engine(
            url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
        )
        self._sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    def session(self) -> AsyncSession:
        return self._sessions()

    async def dispose(self) -> None:
        await self.engine.dispose()
