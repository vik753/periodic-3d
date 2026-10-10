"""Database tables.

Design: "document + index columns". Each compound keeps its card as JSONB (what the
API returns), plus a few real columns for filtering and sorting (elements, fame).
The data is read-only between dataset loads, so there is nothing to normalize for
writes; queries stay simple and fast.

Indexes live in the Alembic migration (migrations/versions/0001_initial.py).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class DatasetRow(Base):
    """The loaded dataset version (one row)."""

    __tablename__ = "dataset"

    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ElementRow(Base):
    __tablename__ = "elements"

    z: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    symbol: Mapped[str] = mapped_column(String(3), unique=True)
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    compound_count: Mapped[int] = mapped_column(Integer, default=0)
    substance: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class CompoundRow(Base):
    __tablename__ = "compounds"

    id: Mapped[str] = mapped_column(String(24), primary_key=True)  # Wikidata QID
    formula: Mapped[str] = mapped_column(Text)
    elements: Mapped[list[str]] = mapped_column(ARRAY(String(3)))  # symbols, by Z
    element_count: Mapped[int] = mapped_column(SmallInteger)
    fame: Mapped[int] = mapped_column(Integer)
    kind: Mapped[str | None] = mapped_column(String(16))  # molecule | crystal | flat
    names: Mapped[dict[str, str]] = mapped_column(JSONB)
    card: Mapped[dict[str, Any]] = mapped_column(JSONB)
    structure: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class PairRow(Base):
    """Two elements (a < b by Z) with the number of shared compounds and the top ones."""

    __tablename__ = "pairs"

    a: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    b: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    count: Mapped[int] = mapped_column(Integer)
    top: Mapped[list[str]] = mapped_column(ARRAY(String(24)))


class ClassRow(Base):
    """Wikidata classes of compounds (oxide, mineral, acid…) with names."""

    __tablename__ = "classes"

    qid: Mapped[str] = mapped_column(String(24), primary_key=True)
    names: Mapped[dict[str, str]] = mapped_column(JSONB)
    count: Mapped[int] = mapped_column(Integer)
