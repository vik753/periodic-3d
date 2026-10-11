"""Static export: every GET answer of the API as a JSON file (ADR 0003).

Layout (paths mirror the API):
    <out>/meta.json                       ↔ /api/v1/meta
    <out>/<version>/elements.json         ↔ /api/v1/elements
    <out>/<version>/elements/Fe.json      ↔ /api/v1/elements/Fe
    <out>/<version>/compounds/Q283.json   ↔ /api/v1/compounds/Q283
    <out>/<version>/pairs/O-Fe.json       ↔ /api/v1/pairs/O-Fe
    <out>/<version>/index.json            ↔ /api/v1/index

The layer of predicted materials (GNoME, ADR 0007) has its own version (meta.gnome):
    <gnome>/materials/pairs.json          ↔ /api/v1/materials/pairs
    <gnome>/materials/shard/517a.json     ↔ /api/v1/materials/shard/517a
    <gnome>/materials/by-element/Ho.json  ↔ /api/v1/materials/by-element/Ho

meta.json is the only unversioned file: the frontend reads it first and then asks for
files of that version, so a new dataset never mixes with cached old files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel

from .db import Database
from .repository import Repository


@dataclass
class ExportReport:
    version: str
    files: int = 0
    bytes: int = 0
    missing: list[str] = field(default_factory=list)
    gnome: str | None = None
    material_files: int = 0
    material_bytes: int = 0


def _write(path: Path, model: BaseModel | str, report: ExportReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = model if isinstance(model, str) else model.model_dump_json(by_alias=True)
    data = text.encode("utf-8")
    path.write_bytes(data)
    report.files += 1
    report.bytes += len(data)


async def export_static(database: Database, out_dir: Path) -> ExportReport:
    async with database.session() as session:
        repo = Repository(session)
        await repo.preload()
        meta = await repo.meta()
        report = ExportReport(version=meta.version)
        root = out_dir / meta.version

        _write(out_dir / "meta.json", meta, report)
        _write(root / "elements.json", await repo.elements(), report)
        for symbol in await repo.element_symbols():
            element = await repo.element(symbol)
            if element is None:
                report.missing.append(f"elements/{symbol}")
                continue
            _write(root / "elements" / f"{symbol}.json", element, report)
        for compound_id in await repo.compound_ids():
            compound = await repo.compound(compound_id)
            if compound is None:
                report.missing.append(f"compounds/{compound_id}")
                continue
            _write(root / "compounds" / f"{compound_id}.json", compound, report)
        for first, second in await repo.pair_symbols():
            pair = await repo.pair(first, second)
            if pair is None:
                report.missing.append(f"pairs/{first}-{second}")
                continue
            _write(root / "pairs" / f"{first}-{second}.json", pair, report)
        _write(root / "index.json", await repo.index(), report)
        if meta.gnome is not None:
            await _export_materials(repo, out_dir / meta.gnome.version, report)
            report.gnome = meta.gnome.version
    return report


async def _export_materials(repo: Repository, root: Path, report: ExportReport) -> None:
    files, size = report.files, report.bytes
    pairs = await repo.material_pairs()
    if pairs is None:
        report.missing.append("materials/pairs")
        return
    _write(root / "materials" / "pairs.json", pairs, report)
    for symbol in await repo.material_symbols():
        listing = await repo.materials_by_element(symbol)
        if listing is None:
            report.missing.append(f"materials/by-element/{symbol}")
            continue
        _write(root / "materials" / "by-element" / f"{symbol}.json", listing, report)
    async for shard in repo.material_shards():
        _write(root / "materials" / "shard" / f"{shard.prefix}.json", shard, report)
    report.material_files = report.files - files
    report.material_bytes = report.bytes - size
