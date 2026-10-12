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


class GnomeInfo(Schema):
    """The loaded layer of predicted materials (GNoME, ADR 0007).

    version names the layer ("gnome-2026.10.11-r3"); in static mode its files live
    under data/<version>/materials/….
    """

    version: str
    created: str
    counts: dict[str, int]
    license: str
    license_url: str | None = None
    citation: str
    source_url: str | None = None


class Meta(Schema):
    version: str
    schema_version: int
    api_version: int
    created: str
    counts: dict[str, int]
    licenses: dict[str, str]
    gnome: GnomeInfo | None = None


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
    # Crystals from Materials Project: "experimental" (matches an ICSD record) or
    # "computed" (calculation only). Absent when unknown (Q.2).
    origin: Literal["experimental", "computed"] | None = None


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


class SimilarElement(Schema):
    """An element with a similar set of partners (vector model)."""

    z: int
    symbol: str
    score: float


class Photo(Schema):
    """A photo from Wikimedia Commons with its attribution (shown under the photo)."""

    url: str
    page: str
    license: str
    author: str | None = None
    license_url: str | None = None


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
    similar: list[SimilarElement] = Field(default_factory=list)
    photo: Photo | None = None
    # Where the element is used (U.2): spheres → terms with sources, quotes, USGS shares.
    uses: dict[str, Any] | None = None


class ClassRef(Schema):
    qid: str
    names: Names


class Source(Schema):
    role: Literal["identity", "description", "properties", "structure", "photo"]
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
    # "pubchem": PubChem's molecular weight; "formula": computed from the formula (Q.1).
    mass_source: Literal["pubchem", "formula"] | None = None
    charge: int = 0
    smiles: str | None = None
    inchikey: str | None = None
    iupac: str | None = None
    classes: list[ClassRef]
    structure_info: StructureInfo | None = None
    structure: dict[str, Any] | None = None
    sources: list[Source]
    similar: list[CompoundSummary] = Field(default_factory=list)
    photo: Photo | None = None
    # Cross-check of sources (Q.1): wikidataFormula (the Wikidata formula was wrong and
    # is fixed), pubchemFormula (PubChem disagrees, no third source decides) or
    # pubchemDropped (the PubChem link led to another substance).
    quality: dict[str, Any] | None = None
    # Where the compound is used (U.2): spheres → terms with sources and quotes.
    uses: dict[str, Any] | None = None


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

    rows: [id, formula, [Z…], fame, kind, names, flags]; flags bit 1 = mineral
    """

    version: str
    fields: list[str]
    rows: list[list[Any]]


class SearchResult(Schema):
    version: str
    query: str
    compounds: list[CompoundSummary]


class MaterialStructure(Schema):
    """Compact unit cell: browsers build the picture (atoms on faces, bonds) themselves.

    cell: a, b, c in ångström and alpha, beta, gamma in degrees.
    sites: base64 of 7-byte records, one per atom: Z (uint8), then the fractional
    coordinates x, y, z times 10⁴ (uint16, little-endian). Binary sites take 40% less
    space than JSON numbers; that keeps the static site under the GitHub Pages limit.
    """

    cell: list[float]
    sites: str


class Material(Schema):
    """A crystal predicted by GNoME: computed, not confirmed by experiment.

    Energies are in eV per atom. decompositionEnergy is the distance to the convex
    hull of competing phases: zero or below means stable in the calculation. The
    database keeps more columns of the source; the API leaves out the ones a visitor
    cannot read (total energy, hull distances against other reference sets) to keep
    the static site under the GitHub Pages limit.
    """

    id: str
    formula: str
    composition: dict[str, int]  # atoms per formula unit
    elements: list[str]  # by atomic number
    nsites: int  # atoms in the unit cell
    space_group: str | None = None
    space_group_number: int | None = None
    point_group: str | None = None
    crystal_system: str | None = None
    volume: float | None = None  # Å³ per cell
    density: float | None = None  # g/cm³
    formation_energy: float | None = None
    decomposition_energy: float | None = None
    # to_camel would write "r2ScanDecompositionEnergy"; keep the pipeline's key.
    r2scan_decomposition_energy: float | None = Field(default=None, alias="r2scanDecompositionEnergy")
    bandgap: float | None = None  # eV
    dimensionality: str | None = None
    structure: MaterialStructure


class MaterialShard(Schema):
    """All predicted materials whose id starts with the same characters (one static file)."""

    version: str
    prefix: str
    materials: list[Material]


class MaterialList(Schema):
    """Every predicted material that contains an element, the simplest and most stable first.

    rows: [id, formula, decompositionEnergy]; the formula names the other elements.
    """

    version: str
    symbol: str
    total: int
    fields: list[str]
    rows: list[list[Any]]


class MaterialPairs(Schema):
    """How many predicted materials each element and each pair of elements has (rays).

    elements: [[Z, count]…]; pairs: [[Za, Zb, count]…] with Za < Zb.
    """

    version: str
    elements: list[list[int]]
    pairs: list[list[int]]


class Health(Schema):
    status: Literal["ok"]
    version: str | None
