"""Initial schema: dataset, elements, compounds, pairs, classes.

Revision ID: 0001
Revises:
Create Date: 2026-10-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "dataset",
        sa.Column("version", sa.String(64), primary_key=True),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "elements",
        sa.Column("z", sa.SmallInteger(), primary_key=True, autoincrement=False),
        sa.Column("symbol", sa.String(3), nullable=False, unique=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("compound_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("substance", postgresql.JSONB(), nullable=True),
    )
    op.create_table(
        "compounds",
        sa.Column("id", sa.String(24), primary_key=True),
        sa.Column("formula", sa.Text(), nullable=False),
        sa.Column("elements", postgresql.ARRAY(sa.String(3)), nullable=False),
        sa.Column("element_count", sa.SmallInteger(), nullable=False),
        sa.Column("fame", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=True),
        sa.Column("names", postgresql.JSONB(), nullable=False),
        sa.Column("card", postgresql.JSONB(), nullable=False),
        sa.Column("structure", postgresql.JSONB(), nullable=True),
    )
    # GIN answers "contains all of these elements" (@>) and "only these" (<@) quickly.
    op.create_index("ix_compounds_elements", "compounds", ["elements"], postgresql_using="gin")
    op.create_index("ix_compounds_fame", "compounds", [sa.text("fame DESC"), "id"])
    op.create_table(
        "pairs",
        sa.Column("a", sa.SmallInteger(), primary_key=True, autoincrement=False),
        sa.Column("b", sa.SmallInteger(), primary_key=True, autoincrement=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("top", postgresql.ARRAY(sa.String(24)), nullable=False),
    )
    op.create_index("ix_pairs_b", "pairs", ["b"])
    op.create_table(
        "classes",
        sa.Column("qid", sa.String(24), primary_key=True),
        sa.Column("names", postgresql.JSONB(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("classes")
    op.drop_index("ix_pairs_b", table_name="pairs")
    op.drop_table("pairs")
    op.drop_index("ix_compounds_fame", table_name="compounds")
    op.drop_index("ix_compounds_elements", table_name="compounds")
    op.drop_table("compounds")
    op.drop_table("elements")
    op.drop_table("dataset")
