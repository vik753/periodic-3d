"""Queries shared by the live API and the static export.

One Repository per request (API) or per export run. It caches the dataset version
and small lookup tables for its lifetime.
"""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.expression import Executable

from . import API_VERSION
from .models import ClassRow, CompoundRow, DatasetRow, ElementRow, PairRow
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
    Meta,
    PairDetail,
    Partner,
    Source,
    StructureInfo,
    Substance,
)

TOP_COMPOUNDS = 12
QUERY_LIMIT_MAX = 200
INDEX_FIELDS = ["id", "formula", "elements", "fame", "kind", "names"]

LICENSE_WIKIDATA = "CC0 1.0"
LICENSE_WIKIPEDIA = "CC BY-SA 4.0"
LICENSE_PUBCHEM = "PubChem (NIH), public data"


class NoDatasetError(RuntimeError):
    """The database has no dataset loaded yet."""


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
            }
        )

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

    async def index(self) -> CompoundIndex:
        version = await self.version()
        z_by_symbol = await self.z_by_symbol()
        rows = await self.session.execute(select(*_SUMMARY_COLUMNS).order_by(CompoundRow.fame.desc(), CompoundRow.id))
        return CompoundIndex(
            version=version,
            fields=INDEX_FIELDS,
            rows=[
                [row.id, row.formula, [z_by_symbol[symbol] for symbol in row.elements], row.fame, row.kind, row.names]
                for row in rows
            ],
        )

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
    return sources
