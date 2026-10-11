"""Per-element lists of predicted materials, built at load time (ADR 0007).

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "material_lists",
        sa.Column("symbol", sa.String(3), primary_key=True),
        sa.Column("total", sa.Integer(), nullable=False),
        sa.Column("rows", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("material_lists")
