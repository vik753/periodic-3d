"""GNoME layer: crystals predicted by Google DeepMind (CC BY-NC 4.0), see ADR 0007.

Output layout (<out>/<version>/):
    manifest.json     version, counts, source files, license, citation
    materials.jsonl   one material per line: properties and the compact cell
    pairs.json        [[Z_a, Z_b, materials], ...] — how many materials each pair has
    elements.json     {symbol: materials}
    report.md         quality report

Compact cell: "cell" = [a, b, c, alpha, beta, gamma] (Å, degrees), "sites" = flat list
[Z, x, y, z, Z, x, y, z, …] with fractional coordinates as integers (× 10 000).
The browser builds the picture (atoms on the faces, bonds) from it.
"""

from __future__ import annotations

import csv
import json
import logging
import math
import re
import time
import zipfile
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

import httpx

from . import __version__
from .elements_table import Z_BY_SYMBOL

log = logging.getLogger("p3d.gnome")

BASE_URL = "https://storage.googleapis.com/gdm_materials_discovery"
SUMMARY_FILE = "gnome_data/stable_materials_summary.csv"
R2SCAN_FILE = "gnome_data/stable_materials_r2scan.csv"
STRUCTURES_FILE = "gnome_data/by_id.zip"
LICENSE = "CC BY-NC 4.0"
LICENSE_URL = "https://creativecommons.org/licenses/by-nc/4.0/"
CITATION = (
    "A. Merchant, S. Batzner, S. S. Schoenholz, M. Aykol, G. Cheon, E. D. Cubuk. "
    "Scaling deep learning for materials discovery. Nature 624, 80–85 (2023). "
    "https://doi.org/10.1038/s41586-023-06735-9"
)
SOURCE_URL = "https://github.com/google-deepmind/materials_discovery"
FRACTION_SCALE = 10_000
USER_AGENT = "periodic-3d/0.1 (https://github.com/vik753/periodic-3d; data pipeline)"

_COMPOSITION = re.compile(r"([A-Z][a-z]?)(\d*\.?\d*)")
_NUMBER = re.compile(r"^[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")
_SYMBOL = re.compile(r"[A-Z][a-z]?")


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------


def download(name: str, cache_dir: Path, *, attempts: int = 3) -> Path:
    """Stream one GNoME file into the cache (skipped when the cached copy is complete)."""
    target = cache_dir / "gnome" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    url = f"{BASE_URL}/{name}"
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=httpx.Timeout(600.0, connect=30.0), headers=headers, follow_redirects=True) as client:
        expected = int(client.head(url).headers.get("Content-Length", "0") or 0)
        if target.exists() and target.stat().st_size == expected > 0:
            log.info("GNoME %s: cached (%d bytes)", name, expected)
            return target
        for attempt in range(1, attempts + 1):
            started = time.monotonic()
            partial = target.with_suffix(target.suffix + ".part")
            try:
                with client.stream("GET", url) as response, partial.open("wb") as handle:
                    response.raise_for_status()
                    for chunk in response.iter_bytes(1 << 20):
                        handle.write(chunk)
                partial.replace(target)
                log.info("GNoME %s: %d bytes in %.0f s", name, target.stat().st_size, time.monotonic() - started)
                return target
            except httpx.HTTPError as error:
                log.warning("GNoME %s: attempt %d failed: %s", name, attempt, error)
                if attempt == attempts:
                    raise
                time.sleep(10 * attempt)
    return target


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _number(text: str) -> float:
    match = _NUMBER.match(text.strip())
    return float(match.group(0)) if match else math.nan


@dataclass
class Cell:
    parameters: list[float]  # a, b, c, alpha, beta, gamma
    sites: list[tuple[int, float, float, float]] = field(default_factory=list)  # Z and fractional x, y, z

    def composition(self) -> Counter[str]:
        symbols = {z: symbol for symbol, z in Z_BY_SYMBOL.items()}
        return Counter(symbols[z] for z, *_ in self.sites)


def parse_cif(text: str) -> Cell | None:
    """Cell and sites of a P1 CIF as GNoME publishes it (pymatgen writer).

    Returns None when the cell is incomplete, a site has an unknown element or a
    partial occupancy (GNoME structures are ordered; anything else is a broken file).
    """
    values: dict[str, str] = {}
    sites: list[tuple[int, float, float, float]] = []
    lines = [line.strip() for line in text.splitlines()]
    index = 0
    while index < len(lines):
        line = lines[index]
        if line == "loop_":
            keys: list[str] = []
            index += 1
            while index < len(lines) and lines[index].startswith("_"):
                keys.append(lines[index].split()[0])
                index += 1
            rows: list[list[str]] = []
            while index < len(lines) and lines[index] and not lines[index].startswith(("_", "loop_", "data_", "#")):
                rows.append(lines[index].split())
                index += 1
            if "_atom_site_fract_x" in keys:
                column = {name: position for position, name in enumerate(keys)}
                symbol_column = column.get("_atom_site_type_symbol", column.get("_atom_site_label", 0))
                for row in rows:
                    if len(row) < len(keys):
                        return None
                    match = _SYMBOL.match(row[symbol_column])
                    if not match or match.group(0) not in Z_BY_SYMBOL:
                        return None
                    occupancy = _number(row[column["_atom_site_occupancy"]]) if "_atom_site_occupancy" in column else 1
                    if abs(occupancy - 1) > 1e-3:
                        return None
                    x, y, z = (_number(row[column[f"_atom_site_fract_{axis}"]]) for axis in "xyz")
                    if any(math.isnan(v) for v in (x, y, z)):
                        return None
                    sites.append((Z_BY_SYMBOL[match.group(0)], x, y, z))
            continue
        if line.startswith("_") and " " in line:
            key, value = line.split(None, 1)
            values[key] = value.strip().strip("'\"")
        index += 1
    names = ("length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma")
    parameters = [_number(values.get(f"_cell_{name}", "nan")) for name in names]
    if any(math.isnan(value) or value <= 0 for value in parameters) or not sites:
        return None
    return Cell(parameters=parameters, sites=sites)


def compact(cell: Cell) -> dict[str, list[float] | list[int]]:
    """The cell as stored in the dataset: 4-decimal parameters, integer fractional coordinates."""
    flat: list[int] = []
    for z, x, y, w in cell.sites:
        flat.append(z)
        flat.extend(round((value % 1.0) * FRACTION_SCALE) % FRACTION_SCALE for value in (x, y, w))
    return {"cell": [round(value, 4) for value in cell.parameters], "sites": flat}


def parse_composition(text: str) -> dict[str, int]:
    """'Cs1S6Zr3' → {'Cs': 1, 'S': 6, 'Zr': 3}."""
    counts: dict[str, int] = {}
    for symbol, amount in _COMPOSITION.findall(text or ""):
        if symbol not in Z_BY_SYMBOL:
            continue
        counts[symbol] = counts.get(symbol, 0) + (int(float(amount)) if amount else 1)
    return counts


def _float(row: dict[str, str], key: str, digits: int) -> float | None:
    value = _number(row.get(key) or "")
    return None if math.isnan(value) else round(value, digits)


def _int(row: dict[str, str], key: str) -> int | None:
    value = _number(row.get(key) or "")
    return None if math.isnan(value) else int(value)


def material_record(row: dict[str, str], cell: Cell, r2scan: dict[str, float]) -> dict[str, Any]:
    """One material for materials.jsonl (camelCase, like the API)."""
    composition = parse_composition(row.get("Composition", ""))
    elements = sorted(composition, key=lambda symbol: Z_BY_SYMBOL[symbol])
    material_id = row["MaterialId"]
    dimensionality = (row.get("Dimensionality Cheon") or "").strip() or None
    record: dict[str, Any] = {
        "id": material_id,
        "formula": row.get("Reduced Formula") or "",
        "composition": {symbol: composition[symbol] for symbol in elements},
        "elements": elements,
        "nsites": len(cell.sites),
        "spaceGroup": row.get("Space Group") or None,
        "spaceGroupNumber": _int(row, "Space Group Number"),
        "pointGroup": row.get("Point Group") or None,
        "crystalSystem": row.get("Crystal System") or None,
        "volume": _float(row, "Volume", 3),
        "density": _float(row, "Density", 4),
        "formationEnergy": _float(row, "Formation Energy Per Atom", 4),
        "decompositionEnergy": _float(row, "Decomposition Energy Per Atom", 4),
        "bandgap": _float(row, "Bandgap", 4),
        "dimensionality": dimensionality if dimensionality != "nan" else None,
        "energy": _float(row, "Corrected Energy", 4),
        "decompositionEnergyAll": _float(row, "Decomposition Energy Per Atom All", 4),
        "decompositionEnergyMp": _float(row, "Decomposition Energy Per Atom MP", 4),
        "decompositionEnergyMpOqmd": _float(row, "Decomposition Energy Per Atom MP OQMD", 4),
        "structure": compact(cell),
    }
    if material_id in r2scan:
        record["r2scanDecompositionEnergy"] = r2scan[material_id]
    return record


def read_summary(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["MaterialId"]: row for row in csv.DictReader(handle) if row.get("MaterialId")}


def read_r2scan(path: Path | None) -> tuple[dict[str, float], list[str]]:
    """r²SCAN decomposition energy per material, if the file has such a column."""
    if path is None or not path.exists():
        return {}, []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        columns = list(reader.fieldnames or [])
        id_column = next((name for name in columns if name.replace(" ", "").lower() == "materialid"), None)
        energy_column = next((name for name in columns if "decomposition" in name.lower()), None)
        if not id_column or not energy_column:
            return {}, columns
        result: dict[str, float] = {}
        for row in reader:
            value = _number(row.get(energy_column) or "")
            if row.get(id_column) and not math.isnan(value):
                result[row[id_column]] = round(value, 4)
        return result, columns


def iter_cifs(path: Path) -> Iterator[tuple[str, str]]:
    """(material id, CIF text) for every file in by_id.zip."""
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".cif"):
                continue
            material_id = Path(info.filename).stem
            yield material_id, archive.read(info).decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


@dataclass
class GnomeOptions:
    out_dir: Path
    cache_dir: Path
    version: str
    limit: int = 0  # keep the first N materials (tests and quick runs)


def run(options: GnomeOptions) -> Path:
    started = time.monotonic()
    root = options.out_dir / options.version
    root.mkdir(parents=True, exist_ok=True)
    summary = read_summary(download(SUMMARY_FILE, options.cache_dir))
    log.info("GNoME summary: %d materials", len(summary))
    try:
        r2scan, r2scan_columns = read_r2scan(download(R2SCAN_FILE, options.cache_dir))
    except httpx.HTTPError as error:
        log.warning("GNoME r2SCAN skipped: %s", error)
        r2scan, r2scan_columns = {}, []
    structures = download(STRUCTURES_FILE, options.cache_dir)

    stats: Counter[str] = Counter()
    pairs: Counter[tuple[int, int]] = Counter()
    per_element: Counter[str] = Counter()
    nsites: list[int] = []
    sizes: list[int] = []
    with (root / "materials.jsonl").open("w", encoding="utf-8") as handle:
        for material_id, text in iter_cifs(structures):
            row = summary.get(material_id)
            if row is None:
                stats["cif_without_summary"] += 1
                continue
            cell = parse_cif(text)
            if cell is None:
                stats["cif_unparsed"] += 1
                continue
            record = material_record(row, cell, r2scan)
            if not record["elements"]:
                stats["no_composition"] += 1
                continue
            reduced_cell = _reduce(cell.composition())
            if reduced_cell != _reduce(Counter(record["composition"])):
                stats["composition_mismatch"] += 1
            line = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
            handle.write(line + "\n")
            sizes.append(len(line))
            nsites.append(record["nsites"])
            stats["materials"] += 1
            if material_id in r2scan:
                stats["with_r2scan"] += 1
            per_element.update(record["elements"])
            zs = sorted(Z_BY_SYMBOL[symbol] for symbol in record["elements"])
            pairs.update(combinations(zs, 2))
            if options.limit and stats["materials"] >= options.limit:
                break
    if not options.limit:
        stats["summary_without_cif"] = max(0, len(summary) - stats["materials"] - stats["cif_unparsed"])

    pair_rows = [[a, b, count] for (a, b), count in sorted(pairs.items())]
    (root / "pairs.json").write_text(json.dumps(pair_rows, separators=(",", ":")), encoding="utf-8")
    (root / "elements.json").write_text(
        json.dumps(dict(sorted(per_element.items(), key=lambda item: Z_BY_SYMBOL[item[0]])), separators=(",", ":")),
        encoding="utf-8",
    )
    seconds = time.monotonic() - started
    manifest = {
        "version": options.version,
        "kind": "gnome",
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "pipeline": __version__,
        "counts": {"materials": stats["materials"], "pairs": len(pair_rows), "elements": len(per_element)},
        "source": {"name": "GNoME (Google DeepMind)", "url": SOURCE_URL, "files": [SUMMARY_FILE, STRUCTURES_FILE]},
        "license": LICENSE,
        "licenseUrl": LICENSE_URL,
        "citation": CITATION,
    }
    (root / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    write_report(root, stats, per_element, pair_rows, nsites, sizes, r2scan_columns, seconds)
    log.info("GNoME layer %s: %d materials in %.0f s", root, stats["materials"], seconds)
    return root


def _reduce(counts: Counter[str]) -> dict[str, float]:
    total = sum(counts.values()) or 1
    return {symbol: round(amount / total, 4) for symbol, amount in counts.items()}


def write_report(
    root: Path,
    stats: Counter[str],
    per_element: Counter[str],
    pairs: list[list[int]],
    nsites: list[int],
    sizes: list[int],
    r2scan_columns: list[str],
    seconds: float,
) -> None:
    def percentile(values: list[int], share: float) -> int:
        ordered = sorted(values)
        return ordered[min(len(ordered) - 1, int(share * len(ordered)))] if ordered else 0

    lines = [
        f"# Отчёт о слое GNoME {root.name}",
        "",
        f"- Материалов: {stats['materials']}; пар элементов: {len(pairs)}; элементов: {len(per_element)}.",
        f"- Атомов в ячейке: медиана {percentile(nsites, 0.5)}, 99% — {percentile(nsites, 0.99)}, "
        f"максимум {max(nsites, default=0)}.",
        f"- Строка материала: медиана {percentile(sizes, 0.5)} байт, всего {sum(sizes) / 1e6:.0f} МБ.",
        f"- Состав ячейки не совпал с формулой: {stats['composition_mismatch']}.",
        f"- CIF не разобран: {stats['cif_unparsed']}; CIF без строки в таблице: {stats['cif_without_summary']}; "
        f"строка без CIF: {stats['summary_without_cif']}.",
        f"- С расчётом r²SCAN: {stats['with_r2scan']} (колонки файла: {', '.join(r2scan_columns[:8])}).",
        f"- Время сборки: {seconds:.0f} с.",
        "",
        "## Элементы — чаще всего",
        "",
    ]
    lines += [f"- {symbol}: {count}" for symbol, count in per_element.most_common(15)]
    lines += ["", f"Лицензия: {LICENSE}. Источник: {CITATION}", ""]
    (root / "report.md").write_text("\n".join(lines), encoding="utf-8")
