"""Build the dataset: elements, compounds, 3D structures, element pairs and a report.

Output layout (data/build/<version>/):
    manifest.json        version, counts, sources and licenses
    elements.json        118 elements with names (en/ru/uk/la) and properties
    compounds.jsonl      one compound card per line (no coordinates)
    pairs.json           element pairs with compound counts and top compounds
    structures/<id>.json 3D structure per compound; element-<Symbol>.json per element
    report.md            quality report
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

from . import __version__
from .chemistry import MOLECULAR_ELEMENTS, NETWORK_SOLIDS, NOBLE_GASES, is_metal
from .elements_table import SYMBOLS, UK_ELEMENT_NAMES, Z_BY_SYMBOL
from .formula import ElementCounts, hill_formula, parse_formula, reduced_formula, same_proportions
from .http import Fetcher
from .sources import optimade, pubchem, wikidata, wikipedia
from .structures import Structure, composition, crystal_fragment, finalize, molecule_from_smiles, parse_sdf

log = logging.getLogger("p3d.build")

SCHEMA_VERSION = 1
STRUCTURE_MAX_BYTES = 80_000
DESCRIPTION_MAX_CHARS = 700
PAIR_TOP = 60

# Allotropes share the formula "C": map the well-known ones to their structures.
ALLOTROPE_STRUCTURES: dict[str, str] = {
    "Q5283": "mp-66",  # diamond
    "Q5309": "mp-48",  # graphite
}

LICENSES = {
    "pubchem": "PubChem (NIH), public data",
    "materialsproject": "CC BY 4.0, Materials Project",
    "wikidata": "CC0, Wikidata",
    "wikipedia": "CC BY-SA 4.0, Wikipedia",
    "rdkit": "Computed with RDKit from PubChem SMILES",
}


@dataclass
class Options:
    out_dir: Path
    cache_dir: Path
    version: str
    only_elements: frozenset[str] | None = None
    limit: int = 0
    descriptions: bool = True
    structures: bool = True


@dataclass
class Compound:
    id: str
    formula: str
    counts: ElementCounts
    names: dict[str, str]
    articles: dict[str, str]
    fame: int
    cid: int | None
    classes: list[str]
    mp_hint: str | None
    descriptions: dict[str, str] = field(default_factory=dict)
    pubchem: dict[str, Any] = field(default_factory=dict)
    structure: dict[str, Any] | None = None

    @property
    def elements(self) -> list[str]:
        return sorted(self.counts, key=lambda symbol: Z_BY_SYMBOL[symbol])

    @property
    def reduced(self) -> str | None:
        return reduced_formula(self.counts)


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------


def _number(value: str | None) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


_KEEP_LOWERCASE = re.compile(r"^[a-z](-|,|\d)")  # n-butane, p-xylene, 1,2-…


def capitalize(text: str) -> str:
    text = text.strip()
    if not text or _KEEP_LOWERCASE.match(text):
        return text
    return text[0].upper() + text[1:]


def _trim(text: str, limit: int = DESCRIPTION_MAX_CHARS) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return cut[: end + 1] if end > limit // 2 else cut.rstrip() + "…"


# ---------------------------------------------------------------------------
# Elements
# ---------------------------------------------------------------------------


def build_elements(table: dict[int, dict[str, str]], labels: dict[int, wikidata.ElementLabels]) -> list[dict[str, Any]]:
    elements = []
    for z, symbol in enumerate(SYMBOLS, start=1):
        cells = table.get(z, {})
        label = labels.get(z)
        names: dict[str, str] = {"en": cells.get("Name") or (label.labels.get("en") if label else None) or symbol}
        substance: dict[str, str] = {}
        if label:
            for language in ("ru", "uk", "la"):
                if language in label.labels:
                    names[language] = capitalize(label.labels[language])
            for language in ("en", "ru", "uk"):
                if language in label.labels:
                    substance[language] = label.labels[language]
        if symbol in UK_ELEMENT_NAMES:
            names["uk"] = UK_ELEMENT_NAMES[symbol]
        hex_color = cells.get("CPKHexColor")
        elements.append(
            {
                "z": z,
                "symbol": symbol,
                "names": {key: capitalize(value) for key, value in names.items()},
                "substanceNames": substance,
                "wikidata": label.qid if label else None,
                "mass": _number(cells.get("AtomicMass")),
                "configuration": cells.get("ElectronConfiguration") or None,
                "electronegativity": _number(cells.get("Electronegativity")),
                "atomicRadius": _number(cells.get("AtomicRadius")),
                "ionizationEnergy": _number(cells.get("IonizationEnergy")),
                "electronAffinity": _number(cells.get("ElectronAffinity")),
                "oxidationStates": cells.get("OxidationStates") or None,
                "standardState": cells.get("StandardState") or None,
                "meltingPoint": _number(cells.get("MeltingPoint")),
                "boilingPoint": _number(cells.get("BoilingPoint")),
                "density": _number(cells.get("Density")),
                "groupBlock": cells.get("GroupBlock") or None,
                "yearDiscovered": cells.get("YearDiscovered") or None,
                "cpk": f"#{hex_color}" if hex_color else None,
            }
        )
    return elements


# ---------------------------------------------------------------------------
# Compounds
# ---------------------------------------------------------------------------


def select_compounds(records: dict[str, wikidata.CompoundRecord], options: Options) -> list[Compound]:
    selected: list[Compound] = []
    for record in records.values():
        counts: ElementCounts | None = None
        display = ""
        for raw in sorted(record.formulas, key=lambda f: (len(f), f)):
            counts = parse_formula(raw)
            if counts:
                display = raw.strip()
                break
        if not counts or not record.articles:
            continue
        if options.only_elements and not set(counts) <= options.only_elements:
            continue
        selected.append(
            Compound(
                id=record.qid,
                formula=display,
                counts=counts,
                names={language: capitalize(text) for language, text in record.labels.items() if text},
                articles=dict(record.articles),
                fame=record.sitelinks or len(record.articles),
                cid=min(record.cids) if record.cids else None,
                classes=sorted(record.classes),
                mp_hint=min(record.mp_ids) if record.mp_ids else None,
            )
        )
    selected.sort(key=lambda compound: (-compound.fame, compound.id))
    if options.limit:
        selected = selected[: options.limit]
    return selected


def prefers_crystal(compound: Compound, has_3d: bool) -> bool:
    """Ionic, metallic and network solids are shown as crystals, molecules as molecules."""
    if compound.id in ALLOTROPE_STRUCTURES:
        return True
    elements = set(compound.counts)
    if compound.reduced in NETWORK_SOLIDS:
        return True
    if len(elements) == 1:
        symbol = next(iter(elements))
        single_atom = abs(compound.counts[symbol] - 1) < 1e-6
        return single_atom and symbol not in MOLECULAR_ELEMENTS and symbol not in NOBLE_GASES and symbol != "C"
    has_metal = any(is_metal(symbol) for symbol in elements)
    smiles = compound.pubchem.get("smiles") or ""
    if has_metal and "C" not in elements:
        return True
    return "." in smiles and not has_3d


def _matches(structure: Structure, counts: ElementCounts) -> bool:
    found = composition(structure)
    if structure.get("kind") == "crystal":
        return same_proportions(found, counts)
    return set(found) == set(counts) and same_proportions(found, counts, tolerance=0.001)


@dataclass
class StructureResult:
    structure: Structure
    source: str
    ref: str | None


def assign_structures(compounds: list[Compound], fetcher: Fetcher) -> tuple[dict[str, StructureResult], Counter[str]]:
    stats: Counter[str] = Counter()
    cids = [compound.cid for compound in compounds if compound.cid]
    log.info("PubChem properties for %d CIDs", len(cids))
    properties = pubchem.properties(fetcher, cids)
    for compound in compounds:
        if compound.cid and compound.cid in properties:
            compound.pubchem = properties[compound.cid]

    log.info("PubChem 3D conformers for %d CIDs", len(cids))
    conformers = pubchem.conformers_3d(fetcher, cids)
    stats["pubchem_3d_available"] = len(conformers)

    wants_crystal = {
        compound.id: prefers_crystal(compound, compound.cid in conformers if compound.cid else False)
        for compound in compounds
    }
    crystal_formulas = {
        compound.reduced
        for compound in compounds
        if compound.reduced
        and compound.id not in ALLOTROPE_STRUCTURES
        and (wants_crystal[compound.id] or not (compound.cid and compound.cid in conformers))
    }
    log.info("OPTIMADE candidates for %d formulas", len(crystal_formulas))
    candidates = optimade.candidates(fetcher, crystal_formulas)
    chosen: dict[str, str] = {}
    for compound in compounds:
        if compound.id in ALLOTROPE_STRUCTURES:
            chosen[compound.id] = ALLOTROPE_STRUCTURES[compound.id]
        elif compound.mp_hint:
            chosen[compound.id] = compound.mp_hint
        elif compound.reduced and (best := optimade.best_candidate(candidates.get(compound.reduced, []))):
            chosen[compound.id] = best.id
    log.info("OPTIMADE structures for %d materials", len(set(chosen.values())))
    crystals = optimade.structures(fetcher, set(chosen.values()))

    results: dict[str, StructureResult] = {}
    for compound in compounds:
        has_3d = bool(compound.cid and compound.cid in conformers)
        methods = ["crystal", "pubchem3d", "rdkit"] if wants_crystal[compound.id] else ["pubchem3d", "rdkit", "crystal"]
        for method in methods:
            structure: Structure | None = None
            ref: str | None = None
            if method == "pubchem3d" and has_3d and compound.cid:
                structure = parse_sdf(conformers[compound.cid])
                ref = str(compound.cid)
            elif method == "rdkit" and compound.pubchem.get("smiles"):
                structure = molecule_from_smiles(compound.pubchem["smiles"])
                ref = str(compound.cid) if compound.cid else None
            elif method == "crystal" and compound.id in chosen and chosen[compound.id] in crystals:
                attributes = crystals[chosen[compound.id]]
                structure = crystal_fragment(
                    attributes.get("lattice_vectors") or [],
                    attributes.get("cartesian_site_positions") or [],
                    attributes.get("species_at_sites") or [],
                )
                ref = chosen[compound.id]
            if structure is None:
                continue
            if not _matches(structure, compound.counts):
                stats[f"rejected_{method}"] += 1
                continue
            source = {"pubchem3d": "pubchem", "rdkit": "rdkit", "crystal": "materialsproject"}[method]
            results[compound.id] = StructureResult(structure=structure, source=source, ref=ref)
            stats[f"structure_{method}_{structure['kind']}"] += 1
            break
        else:
            stats["structure_none"] += 1
    return results, stats


def element_substances(elements: list[dict[str, Any]], fetcher: Fetcher) -> dict[str, StructureResult]:
    """Simple substance of each element: molecule (O₂, S₈…), single atom (noble gases) or crystal."""
    results: dict[str, StructureResult] = {}
    molecular = pubchem.conformers_3d(fetcher, MOLECULAR_ELEMENTS.values())
    crystal_symbols = [
        element["symbol"]
        for element in elements
        if element["symbol"] not in MOLECULAR_ELEMENTS and element["symbol"] not in NOBLE_GASES
    ]
    candidates = optimade.candidates(fetcher, crystal_symbols)
    chosen = {
        symbol: best.id for symbol in crystal_symbols if (best := optimade.best_candidate(candidates.get(symbol, [])))
    }
    chosen.setdefault("C", "mp-48")  # graphite: the standard state of carbon
    crystals = optimade.structures(fetcher, set(chosen.values()))
    for element in elements:
        symbol = element["symbol"]
        if symbol in MOLECULAR_ELEMENTS:
            cid = MOLECULAR_ELEMENTS[symbol]
            if cid in molecular and (structure := parse_sdf(molecular[cid])):
                results[symbol] = StructureResult(structure, "pubchem", str(cid))
        elif symbol in NOBLE_GASES:
            atom = {"el": symbol, "x": 0.0, "y": 0.0, "z": 0.0}
            results[symbol] = StructureResult({"kind": "molecule", "atoms": [atom], "bonds": []}, "pubchem", None)
        elif symbol in chosen and chosen[symbol] in crystals:
            attributes = crystals[chosen[symbol]]
            structure = crystal_fragment(
                attributes.get("lattice_vectors") or [],
                attributes.get("cartesian_site_positions") or [],
                attributes.get("species_at_sites") or [],
            )
            if structure:
                results[symbol] = StructureResult(structure, "materialsproject", chosen[symbol])
    return results


def fetch_descriptions(compounds: list[Compound], fetcher: Fetcher) -> None:
    for language in wikidata.LANGUAGES:
        by_title = {compound.articles[language]: compound for compound in compounds if language in compound.articles}
        log.info("Wikipedia %s extracts for %d articles", language, len(by_title))
        texts = wikipedia.extracts(fetcher, language, by_title)
        for title, text in texts.items():
            by_title[title].descriptions[language] = _trim(text)


def build_pairs(compounds: list[Compound]) -> list[dict[str, Any]]:
    """Element pairs with their compounds, most famous first (compounds are pre-sorted)."""
    pairs: dict[tuple[int, int], list[str]] = defaultdict(list)
    for compound in compounds:
        numbers = sorted(Z_BY_SYMBOL[symbol] for symbol in compound.counts)
        for a, b in combinations(numbers, 2):
            pairs[(a, b)].append(compound.id)
    return [{"a": a, "b": b, "count": len(ids), "top": ids[:PAIR_TOP]} for (a, b), ids in sorted(pairs.items())]


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def _structure_meta(result: StructureResult) -> dict[str, Any]:
    return {
        "kind": result.structure["kind"],
        "source": result.source,
        "ref": result.ref,
        "atoms": len(result.structure["atoms"]),
        "license": LICENSES[result.source],
    }


def compound_card(compound: Compound) -> dict[str, Any]:
    return {
        "id": compound.id,
        "formula": compound.formula,
        "hill": hill_formula(compound.counts),
        "elements": compound.elements,
        "composition": compound.counts,
        "names": compound.names,
        "descriptions": compound.descriptions,
        "articles": compound.articles,
        "fame": compound.fame,
        "pubchemCid": compound.cid,
        "mass": compound.pubchem.get("mass"),
        "charge": compound.pubchem.get("charge", 0),
        "smiles": compound.pubchem.get("smiles"),
        "inchikey": compound.pubchem.get("inchikey"),
        "iupac": compound.pubchem.get("iupac"),
        "classes": compound.classes,
        "structure": compound.structure,
    }


def _write_json(path: Path, data: Any) -> int:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def write_report(
    root: Path,
    compounds: list[Compound],
    elements: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    stats: Counter[str],
    oversized: list[str],
    fetch_stats: Counter[str],
    seconds: float,
) -> None:
    with_structure = [compound for compound in compounds if compound.structure]
    per_element = Counter(symbol for compound in compounds for symbol in compound.counts)
    missing_elements = [element["symbol"] for element in elements if not per_element[element["symbol"]]]
    lines = [
        f"# Отчёт о наборе данных {root.name}",
        "",
        f"- Соединений: {len(compounds)}; с 3D-структурой: {len(with_structure)}.",
        f"- С описанием: RU {sum(1 for c in compounds if 'ru' in c.descriptions)}, "
        f"UK {sum(1 for c in compounds if 'uk' in c.descriptions)}, "
        f"EN {sum(1 for c in compounds if 'en' in c.descriptions)}.",
        f"- С названием: RU {sum(1 for c in compounds if 'ru' in c.names)}, "
        f"UK {sum(1 for c in compounds if 'uk' in c.names)}, EN {sum(1 for c in compounds if 'en' in c.names)}.",
        f"- Пар элементов: {len(pairs)}.",
        f"- Элементов без соединений: {', '.join(missing_elements) or 'нет'}.",
        f"- Структуры больше {STRUCTURE_MAX_BYTES} байт: {len(oversized)} {oversized[:10]}.",
        f"- Время сборки: {seconds:.0f} с.",
        "",
        "## Источники структур",
        "",
        "| Метрика | Значение |",
        "| --- | --- |",
    ]
    lines += [f"| {key} | {value} |" for key, value in sorted(stats.items())]
    lines += ["", "## Запросы", "", "| Метрика | Значение |", "| --- | --- |"]
    lines += [f"| {key} | {value} |" for key, value in sorted(fetch_stats.items())]
    lines += ["", "## Топ-20 соединений", ""]
    for compound in compounds[:20]:
        kind = compound.structure["kind"] if compound.structure else "—"
        name = compound.names.get("ru") or compound.names.get("en") or ""
        lines.append(f"- {compound.formula} — {name} ({compound.fame} статей, {kind})")
    (root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(options: Options) -> Path:
    started = time.monotonic()
    root = options.out_dir / options.version
    (root / "structures").mkdir(parents=True, exist_ok=True)

    with Fetcher(options.cache_dir) as fetcher:
        log.info("Elements")
        elements = build_elements(pubchem.periodic_table(fetcher), wikidata.fetch_element_labels(fetcher))

        log.info("Compounds from Wikidata")
        compounds = select_compounds(wikidata.fetch_compounds(fetcher), options)
        log.info("Selected %d compounds", len(compounds))

        stats: Counter[str] = Counter()
        oversized: list[str] = []
        if options.structures:
            results, stats = assign_structures(compounds, fetcher)
            for compound in compounds:
                result = results.get(compound.id)
                if result is None:
                    continue
                size = _write_json(root / "structures" / f"{compound.id}.json", finalize(result.structure))
                if size > STRUCTURE_MAX_BYTES:
                    oversized.append(compound.id)
                compound.structure = _structure_meta(result)
            for symbol, result in element_substances(elements, fetcher).items():
                _write_json(root / "structures" / f"element-{symbol}.json", finalize(result.structure))
                element = elements[Z_BY_SYMBOL[symbol] - 1]
                element["substance"] = _structure_meta(result)

        if options.descriptions:
            fetch_descriptions(compounds, fetcher)

        pairs = build_pairs(compounds)
        fetch_stats = fetcher.stats

    _write_json(root / "elements.json", elements)
    _write_json(root / "pairs.json", pairs)
    with (root / "compounds.jsonl").open("w", encoding="utf-8") as handle:
        for compound in compounds:
            handle.write(json.dumps(compound_card(compound), ensure_ascii=False, separators=(",", ":")) + "\n")

    seconds = time.monotonic() - started
    manifest = {
        "version": options.version,
        "schema": SCHEMA_VERSION,
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "pipeline": __version__,
        "counts": {
            "elements": len(elements),
            "compounds": len(compounds),
            "structures": sum(1 for compound in compounds if compound.structure),
            "pairs": len(pairs),
        },
        "options": {
            "onlyElements": sorted(options.only_elements) if options.only_elements else None,
            "limit": options.limit,
        },
        "licenses": LICENSES,
    }
    _write_json(root / "manifest.json", manifest)
    write_report(root, compounds, elements, pairs, stats, oversized, fetch_stats, seconds)
    log.info("Dataset %s written in %.0f s", root, seconds)
    return root
