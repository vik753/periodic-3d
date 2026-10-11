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

from sqlalchemy import DateTime, Float, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .vector import Vector

EMBEDDING_DIM = 16
# Predicted materials are grouped by the first characters of their hex id: 16⁴ groups of
# about 8 materials (≈ 5 KB each), so a material card loads one small file (ADR 0007).
MATERIAL_SHARD_CHARS = 4


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
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), deferred=True)


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
    # Normalized formula and names for search (p3d_api.text.search_text); trigram index.
    search: Mapped[str] = mapped_column(Text, default="")
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), deferred=True)


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


class GnomeLayerRow(Base):
    """The loaded GNoME layer version (one row; ADR 0007)."""

    __tablename__ = "gnome_layer"

    version: Mapped[str] = mapped_column(String(64), primary_key=True)
    manifest: Mapped[dict[str, Any]] = mapped_column(JSONB)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MaterialRow(Base):
    """A crystal predicted by GNoME: properties as JSONB, the compact cell, index columns."""

    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    shard: Mapped[str] = mapped_column(String(MATERIAL_SHARD_CHARS))  # first characters of the id
    formula: Mapped[str] = mapped_column(Text)
    elements: Mapped[list[str]] = mapped_column(ARRAY(String(3)))  # symbols, by Z
    element_count: Mapped[int] = mapped_column(SmallInteger)
    decomposition: Mapped[float | None] = mapped_column(Float)  # eV/atom below the hull: lower is more stable
    data: Mapped[dict[str, Any]] = mapped_column(JSONB)
    structure: Mapped[dict[str, Any]] = mapped_column(JSONB)


class MaterialPairRow(Base):
    """Two elements (a < b by Z) and how many predicted materials contain both."""

    __tablename__ = "material_pairs"

    a: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    b: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    count: Mapped[int] = mapped_column(Integer)


class MaterialListRow(Base):
    """Every material with one element, ready to send: computed once at load time.

    rows is a compact JSON array of [id, formula, decompositionEnergy], fewer elements
    first, then the most stable. Iron alone has 25 000 materials: sorting them for
    each request took 0.4 s; reading this row takes milliseconds.
    """

    __tablename__ = "material_lists"

    symbol: Mapped[str] = mapped_column(String(3), primary_key=True)
    total: Mapped[int] = mapped_column(Integer)
    rows: Mapped[str] = mapped_column(Text)
