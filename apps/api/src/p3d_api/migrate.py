"""Run Alembic migrations from code (the CLI and the tests use this)."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config

MIGRATIONS = Path(__file__).parent / "migrations"


def alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    # Passed as an attribute, not an ini option: a '%' in a password would break ini parsing.
    config.attributes["database_url"] = database_url
    return config


def run_migrations(database_url: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(database_url), revision)
