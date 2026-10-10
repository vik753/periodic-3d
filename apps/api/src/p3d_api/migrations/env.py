"""Alembic environment for async SQLAlchemy (asyncpg)."""

from __future__ import annotations

import asyncio
import os

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from p3d_api.models import Base
from p3d_api.settings import DEFAULT_DATABASE_URL, normalize_database_url

config = context.config
target_metadata = Base.metadata


def database_url() -> str:
    url = config.attributes.get("database_url") or os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL
    return normalize_database_url(str(url))


def run_migrations_offline() -> None:
    context.configure(url=database_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(database_url())
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
