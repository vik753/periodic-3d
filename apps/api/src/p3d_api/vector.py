"""pgvector column type without an extra driver dependency.

Values travel as text ('[0.1,0.2,…]') and PostgreSQL casts them to `vector`, so plain
asyncpg works. Vectors are never read back (the columns are deferred): similarity
queries compare rows inside PostgreSQL and return only ids and distances.
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.types import UserDefinedType


class Vector(UserDefinedType[list[float]]):
    cache_ok = True

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def get_col_spec(self, **_: Any) -> str:
        return f"vector({self.dim})"

    def bind_processor(self, dialect: Any) -> Any:
        def process(value: list[float] | None) -> str | None:
            if value is None:
                return None
            return "[" + ",".join(f"{float(x):.6g}" for x in value) + "]"

        return process

    def bind_expression(self, bindvalue: Any) -> Any:
        return sa.cast(sa.cast(bindvalue, sa.Text), self)


def cosine_distance(column: Any, other: Any) -> sa.ColumnElement[float]:
    """pgvector cosine distance: 0 for the same direction, 2 for the opposite one."""
    return column.op("<=>", return_type=sa.Float)(other)  # type: ignore[no-any-return]
