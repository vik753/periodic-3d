"""Queries shared by the live API and the static export.

One Repository per request (API) or per export run. It caches the dataset version
and small lookup tables for its lifetime.
"""

from __future__ import annotations

import base64
import json
import struct
from collections.abc import AsyncIterator
from typing import Any, Literal
from urllib.parse import quote

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Executable

from . import API_VERSION
from .models import (
    MATERIAL_SHARD_CHARS,
    ClassRow,
    CompoundRow,
    DatasetRow,
    ElementRow,
    GnomeLayerRow,
    MaterialListRow,
    MaterialPairRow,
    MaterialRow,
    PairRow,
)
from .schemas import (
    ClassRef,
    CompoundDetail,
    CompoundIndex,
    CompoundQuery,
    CompoundSummary,
    ElementDetail,
    ElementList,
    ElementRef,
    ElementSummary,
    GnomeInfo,
    Material,
    MaterialPairs,
    MaterialShard,
    Meta,
    PairDetail,
    Partner,
    SearchResult,
    SimilarElement,
    Source,
    StructureInfo,
    Substance,
)
from .text import normalize_text
from .vector import cosine_distance

TOP_COMPOUNDS = 12
SIMILAR_ELEMENTS = 6
SIMILAR_COMPOUNDS = 8
SIMILAR_CANDIDATES = 40  # pgvector's default hnsw.ef_search: an index scan returns at most 40 rows
# Vectors of rare elements are noise (curium sits next to carbon: both meet only C, H, N, O).
# An element takes part in similarity only with at least this share of all compounds
# (about 54 of 27 000), and a neighbour needs at least this cosine similarity.
SIMILAR_MIN_SHARE = 0.002
SIMILAR_MIN_SCORE = 0.3
QUERY_LIMIT_MAX = 200
INDEX_FIELDS = ["id", "formula", "elements", "fame", "kind", "names", "flags"]
# Bits of the "flags" index column (filters in the browser).
FLAG_MINERAL = 1
CLASS_MINERAL_SPECIES = "Q12089225"

LICENSE_WIKIDATA = "CC0 1.0"
LICENSE_WIKIPEDIA = "CC BY-SA 4.0"
LICENSE_PUBCHEM = "PubChem (NIH), public data"
MATERIAL_LIST_FIELDS = ["id", "formula", "decompositionEnergy"]
HEX_DIGITS = frozenset("0123456789abcdef")
SITE_RECORD = struct.Struct("<BHHH")  # Z, x·10⁴, y·10⁴, z·10⁴


class NoDatasetError(RuntimeError):
    """The database has no dataset loaded yet."""


def encode_sites(flat: list[int]) -> str:
    """[Z, x, y, z, …] (coordinates ×10⁴) → base64 of 7-byte records (MaterialStructure)."""
    buffer = bytearray()
    for index in range(0, len(flat) - 3, 4):
        buffer += SITE_RECORD.pack(*flat[index : index + 4])
    return base64.b64encode(bytes(buffer)).decode("ascii")


def material_from_row(data: dict[str, Any], structure: dict[str, Any]) -> Material:
    compact = {"cell": structure.get("cell", []), "sites": encode_sites(structure.get("sites", []))}
    return Material.model_validate({**data, "structure": compact})


def valid_shard(prefix: str) -> str | None:
    prefix = prefix.strip().lower()
    return prefix if len(prefix) == MATERIAL_SHARD_CHARS and set(prefix) <= HEX_DIGITS else None


def normalize_symbol(symbol: str) -> str:
    symbol = symbol.strip()
    return symbol[:1].upper() + symbol[1:].lower()


def normalize_compound_id(compound_id: str) -> str:
    return compound_id.strip().upper()


_SUMMARY_COLUMNS = (
    CompoundRow.id,
    CompoundRow.formula,
    CompoundRow.names,
    CompoundRow.elements,
    CompoundRow.fame,
    CompoundRow.kind,
)


def _summary(row: Any) -> CompoundSummary:
    return CompoundSummary(
        id=row.id,
        formula=row.formula,
        names=row.names,
        elements=list(row.elements),
        fame=row.fame,
        kind=row.kind,
    )


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._version: str | None = None
        self._manifest: dict[str, Any] | None = None
        self._z_by_symbol: dict[str, int] | None = None
        self._classes: dict[str, dict[str, str]] | None = None
        self._gnome: tuple[str, dict[str, Any]] | None = None
        self._gnome_checked = False

    # -- lookups -------------------------------------------------------------

    async def version(self) -> str:
        if self._version is None:
            row = (await self.session.execute(select(DatasetRow.version, DatasetRow.manifest).limit(1))).first()
            if row is None:
                raise NoDatasetError("no dataset is loaded")
            self._version, self._manifest = row.version, row.manifest
        return self._version

    async def z_by_symbol(self) -> dict[str, int]:
        if self._z_by_symbol is None:
            rows = await self.session.execute(select(ElementRow.symbol, ElementRow.z))
            self._z_by_symbol = {row.symbol: row.z for row in rows}
        return self._z_by_symbol

    async def gnome(self) -> tuple[str, dict[str, Any]] | None:
        """Version and manifest of the predicted-materials layer, or None if none is loaded."""
        if not self._gnome_checked:
            row = (await self.session.execute(select(GnomeLayerRow.version, GnomeLayerRow.manifest).limit(1))).first()
            self._gnome = (row.version, row.manifest) if row is not None else None
            self._gnome_checked = True
        return self._gnome

    async def preload(self) -> None:
        """Load all lookup tables at once (for the static export)."""
        await self.version()
        await self.z_by_symbol()
        rows = await self.session.execute(select(ClassRow.qid, ClassRow.names))
        self._classes = {row.qid: row.names for row in rows}

    async def _class_names(self, qids: list[str]) -> dict[str, dict[str, str]]:
        if self._classes is not None:
            return {qid: self._classes[qid] for qid in qids if qid in self._classes}
        if not qids:
            return {}
        rows = await self.session.execute(select(ClassRow.qid, ClassRow.names).where(ClassRow.qid.in_(qids)))
        return {row.qid: row.names for row in rows}

    async def _summaries(self, statement: Executable) -> list[CompoundSummary]:
        return [_summary(row) for row in await self.session.execute(statement)]

    # -- endpoints -----------------------------------------------------------

    async def meta(self) -> Meta:
        version = await self.version()
        manifest = self._manifest or {}
        return Meta(
            version=version,
            schema_version=int(manifest.get("schema", 1)),
            api_version=API_VERSION,
            created=str(manifest.get("created", "")),
            counts={key: int(value) for key, value in manifest.get("counts", {}).items()},
            licenses={key: str(value) for key, value in manifest.get("licenses", {}).items()},
            gnome=await self.gnome_info(),
        )

    async def gnome_info(self) -> GnomeInfo | None:
        layer = await self.gnome()
        if layer is None:
            return None
        version, manifest = layer
        source = manifest.get("source") or {}
        return GnomeInfo(
            version=version,
            created=str(manifest.get("created", "")),
            counts={key: int(value) for key, value in manifest.get("counts", {}).items()},
            license=str(manifest.get("license", "")),
            license_url=manifest.get("licenseUrl"),
            citation=str(manifest.get("citation", "")),
            source_url=source.get("url"),
        )

    async def elements(self) -> ElementList:
        version = await self.version()
        rows = (await self.session.execute(select(ElementRow).order_by(ElementRow.z))).scalars().all()
        return ElementList(
            version=version,
            elements=[
                ElementSummary(
                    z=row.z,
                    symbol=row.symbol,
                    names=row.data.get("names", {}),
                    mass=row.data.get("mass"),
                    group_block=row.data.get("groupBlock"),
                    standard_state=row.data.get("standardState"),
                    cpk=row.data.get("cpk"),
                    compound_count=row.compound_count,
                    has_substance=row.substance is not None,
                )
                for row in rows
            ],
        )

    async def element(self, symbol: str) -> ElementDetail | None:
        version = await self.version()
        row = await self.session.scalar(select(ElementRow).where(ElementRow.symbol == normalize_symbol(symbol)))
        if row is None:
            return None
        symbols = {z: s for s, z in (await self.z_by_symbol()).items()}
        pairs = await self.session.execute(
            select(PairRow.a, PairRow.b, PairRow.count)
            .where(or_(PairRow.a == row.z, PairRow.b == row.z))
            .order_by(PairRow.count.desc(), PairRow.a, PairRow.b)
        )
        partners = []
        for pair in pairs:
            other = pair.b if pair.a == row.z else pair.a
            partners.append(Partner(z=other, symbol=symbols.get(other, "?"), count=pair.count))
        top = await self._summaries(
            select(*_SUMMARY_COLUMNS)
            .where(CompoundRow.elements.contains([row.symbol]))
            .order_by(CompoundRow.fame.desc(), CompoundRow.id)
            .limit(TOP_COMPOUNDS)
        )
        data = dict(row.data)
        substance_info = data.pop("substance", None)
        substance = None
        if row.substance is not None and substance_info:
            substance = Substance(
                names=data.get("substanceNames", {}),
                info=StructureInfo.model_validate(substance_info),
                structure=row.substance,
            )
        return ElementDetail.model_validate(
            {
                **data,
                "version": version,
                "compoundCount": row.compound_count,
                "substance": substance,
                "partners": partners,
                "topCompounds": top,
                "similar": await self.similar_elements(row.z),
            }
        )

    async def compound_total(self) -> int:
        await self.version()
        counts = (self._manifest or {}).get("counts", {})
        return int(counts.get("compounds", 0))

    async def similar_elements(self, z: int) -> list[SimilarElement]:
        """Elements with the closest vectors (cosine distance, pgvector); common elements only."""
        min_count = max(1, round(await self.compound_total() * SIMILAR_MIN_SHARE))
        own_count = await self.session.scalar(select(ElementRow.compound_count).where(ElementRow.z == z))
        if own_count is None or own_count < min_count:
            return []
        target = select(ElementRow.embedding).where(ElementRow.z == z).scalar_subquery()
        distance = cosine_distance(ElementRow.embedding, target).label("distance")
        rows = await self.session.execute(
            select(ElementRow.z, ElementRow.symbol, distance)
            .where(
                ElementRow.z != z,
                ElementRow.embedding.is_not(None),
                ElementRow.compound_count >= min_count,
                distance <= 1 - SIMILAR_MIN_SCORE,
            )
            .order_by(distance, ElementRow.z)
            .limit(SIMILAR_ELEMENTS)
        )
        return [
            SimilarElement(z=row.z, symbol=row.symbol, score=round(1 - float(row.distance), 3))
            for row in rows
            if row.distance is not None
        ]

    async def similar_compounds(self, compound_id: str) -> list[CompoundSummary]:
        """Compounds with the closest vectors: similar elements in similar proportions.

        The HNSW index answers only "ORDER BY distance LIMIT k". It returns the nearest
        SIMILAR_CANDIDATES; among near-equal distances the more famous compounds win.
        """
        target = select(CompoundRow.embedding).where(CompoundRow.id == compound_id).scalar_subquery()
        distance = cosine_distance(CompoundRow.embedding, target).label("distance")
        rows = (
            await self.session.execute(select(*_SUMMARY_COLUMNS, distance).order_by(distance).limit(SIMILAR_CANDIDATES))
        ).all()
        ranked = sorted(
            (row for row in rows if row.id != compound_id and row.distance is not None),
            key=lambda row: (round(float(row.distance), 3), -row.fame, row.id),
        )
        return [_summary(row) for row in ranked[:SIMILAR_COMPOUNDS]]

    async def compound(self, compound_id: str) -> CompoundDetail | None:
        version = await self.version()
        row = await self.session.get(CompoundRow, normalize_compound_id(compound_id))
        if row is None:
            return None
        card = row.card
        class_ids = [str(qid) for qid in card.get("classes", [])]
        class_names = await self._class_names(class_ids)
        payload = {key: value for key, value in card.items() if key not in ("structure", "classes", "articles")}
        payload.update(
            version=version,
            classes=[ClassRef(qid=qid, names=class_names.get(qid, {})) for qid in class_ids],
            structureInfo=card.get("structure") if row.structure is not None else None,
            structure=row.structure,
            sources=compound_sources(card, has_structure=row.structure is not None),
            similar=await self.similar_compounds(row.id),
        )
        return CompoundDetail.model_validate(payload)

    async def pair(self, first: str, second: str) -> PairDetail | None:
        version = await self.version()
        z_by_symbol = await self.z_by_symbol()
        za, zb = z_by_symbol.get(normalize_symbol(first)), z_by_symbol.get(normalize_symbol(second))
        if za is None or zb is None or za == zb:
            return None
        a, b = sorted((za, zb))
        row = await self.session.get(PairRow, (a, b))
        if row is None:
            return None
        order = {compound_id: index for index, compound_id in enumerate(row.top)}
        compounds = await self._summaries(select(*_SUMMARY_COLUMNS).where(CompoundRow.id.in_(row.top)))
        compounds.sort(key=lambda compound: order[compound.id])
        symbols = {z: s for s, z in z_by_symbol.items()}
        return PairDetail(
            version=version,
            a=ElementRef(z=a, symbol=symbols[a]),
            b=ElementRef(z=b, symbol=symbols[b]),
            count=row.count,
            compounds=compounds,
        )

    async def query(
        self,
        symbols: list[str],
        mode: Literal["contains", "only"] = "contains",
        limit: int = 60,
        offset: int = 0,
    ) -> CompoundQuery:
        """Compounds that contain all the given elements ('contains') or exactly them ('only')."""
        version = await self.version()
        z_by_symbol = await self.z_by_symbol()
        selected = sorted(
            {normalize_symbol(symbol) for symbol in symbols if symbol.strip()}, key=lambda s: z_by_symbol.get(s, 999)
        )
        if not selected:
            raise ValueError("select at least one element")
        unknown = [symbol for symbol in selected if symbol not in z_by_symbol]
        if unknown:
            raise ValueError(f"unknown elements: {', '.join(unknown)}")
        condition = CompoundRow.elements.contains(selected)
        if mode == "only":
            condition = condition & CompoundRow.elements.contained_by(selected)
        total = await self.session.scalar(select(func.count()).select_from(CompoundRow).where(condition)) or 0
        compounds = await self._summaries(
            select(*_SUMMARY_COLUMNS)
            .where(condition)
            .order_by(CompoundRow.fame.desc(), CompoundRow.id)
            .limit(min(limit, QUERY_LIMIT_MAX))
            .offset(offset)
        )
        return CompoundQuery(version=version, elements=selected, mode=mode, total=total, compounds=compounds)

    async def search(self, query: str, limit: int = 20) -> SearchResult:
        """Compounds whose formula or name contains the query; exact formulas and famous ones first."""
        version = await self.version()
        needle = normalize_text(query)
        if not needle:
            return SearchResult(version=version, query=query, compounds=[])
        pattern = "%" + needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        compact = needle.replace(" ", "")
        exact = CompoundRow.search.startswith(compact + " |", autoescape=True)
        statement = (
            select(*_SUMMARY_COLUMNS)
            .where(CompoundRow.search.ilike(pattern))
            .order_by(exact.desc(), func.similarity(CompoundRow.search, needle).desc(), CompoundRow.fame.desc())
            .limit(min(limit, QUERY_LIMIT_MAX))
        )
        return SearchResult(version=version, query=query, compounds=await self._summaries(statement))

    async def index(self) -> CompoundIndex:
        version = await self.version()
        z_by_symbol = await self.z_by_symbol()
        classes = CompoundRow.card["classes"].label("classes")
        rows = await self.session.execute(
            select(*_SUMMARY_COLUMNS, classes).order_by(CompoundRow.fame.desc(), CompoundRow.id)
        )
        return CompoundIndex(
            version=version,
            fields=INDEX_FIELDS,
            rows=[
                [
                    row.id,
                    row.formula,
                    [z_by_symbol[symbol] for symbol in row.elements],
                    row.fame,
                    row.kind,
                    row.names,
                    FLAG_MINERAL if CLASS_MINERAL_SPECIES in (row.classes or []) else 0,
                ]
                for row in rows
            ],
        )

    # -- predicted materials (GNoME layer, ADR 0007) --------------------------

    async def material_shard(self, prefix: str) -> MaterialShard | None:
        layer = await self.gnome()
        shard = valid_shard(prefix)
        if layer is None or shard is None:
            return None
        statement = (
            select(MaterialRow.data, MaterialRow.structure).where(MaterialRow.shard == shard).order_by(MaterialRow.id)
        )
        rows = (await self.session.execute(statement)).all()
        if not rows:
            return None
        return MaterialShard(
            version=layer[0], prefix=shard, materials=[material_from_row(row.data, row.structure) for row in rows]
        )

    async def materials_by_element(self, symbol: str) -> str | None:
        """All materials with the element as JSON text (MaterialList): fewer elements first,
        then the most stable. The rows were built at load time; the text goes out as is.
        """
        layer = await self.gnome()
        if layer is None:
            return None
        symbol = normalize_symbol(symbol)
        row = await self.session.get(MaterialListRow, symbol)
        if row is None or row.total == 0:
            return None
        head = {"version": layer[0], "symbol": symbol, "total": row.total, "fields": MATERIAL_LIST_FIELDS}
        return json.dumps(head, separators=(",", ":"))[:-1] + ',"rows":' + row.rows + "}"

    async def material_pairs(self) -> MaterialPairs | None:
        layer = await self.gnome()
        if layer is None:
            return None
        version, manifest = layer
        z_by_symbol = await self.z_by_symbol()
        counts = manifest.get("elements") or {}
        elements = sorted(
            [z_by_symbol[symbol], int(count)] for symbol, count in counts.items() if symbol in z_by_symbol
        )
        rows = await self.session.execute(
            select(MaterialPairRow.a, MaterialPairRow.b, MaterialPairRow.count).order_by(
                MaterialPairRow.a, MaterialPairRow.b
            )
        )
        return MaterialPairs(version=version, elements=elements, pairs=[[row.a, row.b, row.count] for row in rows])

    async def material_symbols(self) -> list[str]:
        layer = await self.gnome()
        return sorted((layer[1].get("elements") or {}) if layer else {})

    async def material_shards(self) -> AsyncIterator[MaterialShard]:
        """Every shard in id order, read in one pass (the static export writes 65 536 files)."""
        layer = await self.gnome()
        if layer is None:
            return
        statement = select(MaterialRow.shard, MaterialRow.data, MaterialRow.structure).order_by(MaterialRow.id)
        current: str | None = None
        materials: list[Material] = []
        async for row in await self.session.stream(statement.execution_options(yield_per=5000)):
            if row.shard != current and materials:
                yield MaterialShard(version=layer[0], prefix=str(current), materials=materials)
                materials = []
            current = row.shard
            materials.append(material_from_row(row.data, row.structure))
        if materials:
            yield MaterialShard(version=layer[0], prefix=str(current), materials=materials)

    # -- export helpers ------------------------------------------------------

    async def element_symbols(self) -> list[str]:
        return list((await self.session.execute(select(ElementRow.symbol).order_by(ElementRow.z))).scalars())

    async def compound_ids(self) -> list[str]:
        return list((await self.session.execute(select(CompoundRow.id).order_by(CompoundRow.id))).scalars())

    async def pair_symbols(self) -> list[tuple[str, str]]:
        symbols = {z: s for s, z in (await self.z_by_symbol()).items()}
        rows = await self.session.execute(select(PairRow.a, PairRow.b).order_by(PairRow.a, PairRow.b))
        return [(symbols[row.a], symbols[row.b]) for row in rows]


def wikipedia_url(language: str, title: str) -> str:
    return f"https://{language}.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"


def compound_sources(card: dict[str, Any], *, has_structure: bool) -> list[Source]:
    """Where each part of the card comes from, with licenses (shown in the card footer)."""
    sources = [
        Source(
            role="identity",
            name="Wikidata",
            url=f"https://www.wikidata.org/wiki/{card['id']}",
            license=LICENSE_WIKIDATA,
        )
    ]
    for language, title in sorted(card.get("articles", {}).items()):
        sources.append(
            Source(
                role="description",
                name=f"Wikipedia ({language})",
                url=wikipedia_url(language, title),
                license=LICENSE_WIKIPEDIA,
            )
        )
    if card.get("pubchemCid"):
        sources.append(
            Source(
                role="properties",
                name="PubChem",
                url=f"https://pubchem.ncbi.nlm.nih.gov/compound/{card['pubchemCid']}",
                license=LICENSE_PUBCHEM,
            )
        )
    info = card.get("structure")
    if has_structure and info:
        source, ref = info.get("source"), info.get("ref")
        if source == "materialsproject":
            name, url = "Materials Project", f"https://next-gen.materialsproject.org/materials/{ref}" if ref else None
        elif source == "pubchem":
            name, url = (
                "PubChem 3D",
                f"https://pubchem.ncbi.nlm.nih.gov/compound/{ref}#section=3D-Conformer" if ref else None,
            )
        else:
            name, url = "RDKit", None
        sources.append(Source(role="structure", name=name, url=url, license=str(info.get("license", ""))))
    photo = card.get("photo")
    if photo:
        sources.append(
            Source(role="photo", name="Wikimedia Commons", url=photo.get("page"), license=str(photo.get("license", "")))
        )
    return sources
