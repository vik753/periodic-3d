"""GNoME layer: predicted materials and their element pairs (ADR 0007).

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gnome_layer",
        sa.Column("version", sa.String(64), primary_key=True),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("loaded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "materials",
        sa.Column("id", sa.String(16), primary_key=True),
        sa.Column("shard", sa.String(4), nullable=False),
        sa.Column("formula", sa.Text(), nullable=False),
        sa.Column("elements", postgresql.ARRAY(sa.String(3)), nullable=False),
        sa.Column("element_count", sa.SmallInteger(), nullable=False),
        sa.Column("decomposition", sa.Float(), nullable=True),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("structure", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_materials_shard", "materials", ["shard"])
    op.create_index("ix_materials_elements", "materials", ["elements"], postgresql_using="gin")
    op.create_table(
        "material_pairs",
        sa.Column("a", sa.SmallInteger(), primary_key=True, autoincrement=False),
        sa.Column("b", sa.SmallInteger(), primary_key=True, autoincrement=False),
        sa.Column("count", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("material_pairs")
    op.drop_index("ix_materials_elements", table_name="materials")
    op.drop_index("ix_materials_shard", table_name="materials")
    op.drop_table("materials")
    op.drop_table("gnome_layer")
