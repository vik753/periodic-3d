"""Search: normalized text per compound with a trigram index (pg_trgm).

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pg_trgm splits text into 3-letter pieces; a GIN index on them answers
    # "contains this substring" (ILIKE '%вод%') without scanning every row.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.add_column("compounds", sa.Column("search", sa.Text(), nullable=False, server_default=""))
    op.execute("CREATE INDEX ix_compounds_search ON compounds USING gin (search gin_trgm_ops)")


def downgrade() -> None:
    op.drop_index("ix_compounds_search", table_name="compounds")
    op.drop_column("compounds", "search")
