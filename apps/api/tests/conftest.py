"""Test setup. API tests need PostgreSQL: set TEST_DATABASE_URL (CI starts a service container)."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "dataset"
VERSION = "2026.01.01-test"


@pytest.fixture(scope="session")
def database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not set")
    from p3d_api.settings import normalize_database_url

    return normalize_database_url(url)


@pytest.fixture(scope="session")
def loaded_database(database_url: str) -> str:
    """Migrate the schema and load the fixture dataset once per test session."""
    from p3d_api.db import Database
    from p3d_api.loader import load_dataset, open_dataset
    from p3d_api.migrate import run_migrations

    run_migrations(database_url)

    async def load() -> None:
        database = Database(database_url)
        try:
            with open_dataset(FIXTURE) as root:
                await load_dataset(database.engine, root)
        finally:
            await database.dispose()

    asyncio.run(load())
    return database_url


@pytest.fixture
async def client(loaded_database: str) -> AsyncIterator[object]:
    import httpx

    from p3d_api.app import create_app
    from p3d_api.settings import Settings

    app = create_app(Settings(database_url=loaded_database, version_ttl=0.0, build_id="test"))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    await app.state.database.dispose()
