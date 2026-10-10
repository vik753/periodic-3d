"""Vectors: 16-dimensional embeddings of elements and compounds (pgvector).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-11
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DIM = 16


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(f"ALTER TABLE elements ADD COLUMN embedding vector({DIM})")
    op.execute(f"ALTER TABLE compounds ADD COLUMN embedding vector({DIM})")
    # HNSW: approximate nearest neighbours by cosine distance in a few milliseconds.
    op.execute("CREATE INDEX ix_compounds_embedding ON compounds USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_compounds_embedding")
    op.execute("ALTER TABLE compounds DROP COLUMN IF EXISTS embedding")
    op.execute("ALTER TABLE elements DROP COLUMN IF EXISTS embedding")
