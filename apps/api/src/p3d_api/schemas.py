"""Response shapes. JSON keys are camelCase; the frontend types mirror these models.

The same models serve the live API and the static export (ADR 0003), so both data
modes return identical JSON.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

Names = dict[str, str]  # language code (en, ru, uk, la) → text


class Schema(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Meta(Schema):
    version: str
    schema_version: int
    api_version: int
    created: str
    counts: dict[str, int]
    licenses: dict[str, str]


class ElementSummary(Schema):
    z: int
    symbol: str
    names: Names
    mass: float | None = None
    group_block: str | None = None
    standard_state: str | None = None
    cpk: str | None = None
    compound_count: int = 0
    has_substance: bool = False


class ElementList(Schema):
    version: str
    elements: list[ElementSummary]


class StructureInfo(Schema):
    """Where a 3D structure comes from."""

    kind: str  # molecule | crystal | flat
    source: str  # pubchem | rdkit | materialsproject
    ref: str | None = None
    atoms: int
    license: str


class Substance(Schema):
    """The simple substance of an element (O₂, graphite, bcc iron…)."""

    names: Names
    info: StructureInfo
    structure: dict[str, Any]


class Partner(Schema):
    """Another element that forms compounds with this one: one glowing ray."""

    z: int
    symbol: str
    count: int


class CompoundSummary(Schema):
    id: str
    formula: str
    names: Names
    elements: list[str]
    fame: int
    kind: str | None = None


class ElementDetail(Schema):
    version: str
    z: int
    symbol: str
    names: Names
    substance_names: Names = Field(default_factory=dict)
    wikidata: str | None = None
    mass: float | None = None
    configuration: str | None = None
    electronegativity: float | None = None
    atomic_radius: float | None = None
    ionization_energy: float | None = None
    electron_affinity: float | None = None
    oxidation_states: str | None = None
    standard_state: str | None = None
    melting_point: float | None = None
    boiling_point: float | None = None
    density: float | None = None
    group_block: str | None = None
    year_discovered: str | None = None
    cpk: str | None = None
    compound_count: int = 0
    substance: Substance | None = None
    partners: list[Partner]
    top_compounds: list[CompoundSummary]


class ClassRef(Schema):
    qid: str
    names: Names


class Source(Schema):
    role: Literal["identity", "description", "properties", "structure"]
    name: str
    url: str | None = None
    license: str


class CompoundDetail(Schema):
    version: str
    id: str
    formula: str
    hill: str
    elements: list[str]
    composition: dict[str, float]
    names: Names
    descriptions: Names
    fame: int
    pubchem_cid: int | None = None
    mass: float | None = None
    charge: int = 0
    smiles: str | None = None
    inchikey: str | None = None
    iupac: str | None = None
    classes: list[ClassRef]
    structure_info: StructureInfo | None = None
    structure: dict[str, Any] | None = None
    sources: list[Source]


class ElementRef(Schema):
    z: int
    symbol: str


class PairDetail(Schema):
    """Compounds of two elements: the beads along one ray."""

    version: str
    a: ElementRef
    b: ElementRef
    count: int
    compounds: list[CompoundSummary]


class CompoundQuery(Schema):
    """Compounds for a multi-element selection: the cloud."""

    version: str
    elements: list[str]
    mode: Literal["contains", "only"]
    total: int
    compounds: list[CompoundSummary]


class CompoundIndex(Schema):
    """Compact list of all compounds for search and selection in the browser (static mode).

    rows: [id, formula, [Z…], fame, kind, names]
    """

    version: str
    fields: list[str]
    rows: list[list[Any]]


class Health(Schema):
    status: Literal["ok"]
    version: str | None
