"""Build the dataset: elements, compounds, 3D structures, element pairs and a report.

Output layout (data/build/<version>/):
    manifest.json        version, counts, sources and licenses
    elements.json        118 elements with names (en/ru/uk/la) and properties
    compounds.jsonl      one compound card per line (no coordinates)
    pairs.json           element pairs with compound counts and top compounds
    classes.json         Wikidata classes of the compounds with labels (en/ru/uk)
    vectors.json         16-dimensional vectors of elements and compounds (similarity)
    structures/<id>.json 3D structure per compound; element-<Symbol>.json per element
    report.md            quality report
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from dataclasses import dataclass, field
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from typing import Any

from . import __version__, embeddings
from .chemistry import (
    CLASS_MINERAL_SPECIES,
    EXCLUDED_CLASSES,
    MAX_FORMULA_ATOMS,
    MOLECULAR_ELEMENTS,
    MOLECULAR_SMILES,
    NETWORK_SOLIDS,
    NOBLE_GASES,
    REPRESENTATIVE_SMILES,
    is_metal,
)
from .elements_table import SYMBOLS, UK_ELEMENT_NAMES, Z_BY_SYMBOL
from .formula import (
    ElementCounts,
    conventional_formula,
    display_formula,
    has_net_charge,
    hill_formula,
    net_charge,
    parse_formula,
    reduced_formula,
    same_proportions,
    to_subscripts,
)
from .http import Fetcher
from .quality import FormulaCheck, Verdict, check_formula, has_isotopes, molar_mass, plain_formula
from .sources import commons, mp_api, optimade, pubchem, wikidata, wikipedia
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
    "rdkit": "Computed with RDKit from SMILES (PubChem, Wikidata)",
    "commons": "Wikimedia Commons, license per photo",
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
    charged: bool = False
    wikidata_smiles: str | None = None
    image: str | None = None  # Commons file name (Wikidata P18)
    photo: dict[str, str] | None = None
    descriptions: dict[str, str] = field(default_factory=dict)
    pubchem: dict[str, Any] = field(default_factory=dict)
    structure: dict[str, Any] | None = None
    mass: float | None = None
    mass_source: str | None = None  # "pubchem" or "formula"
    # Cross-check results shown in the card (Q.1): a fixed formula, a dropped PubChem link,
    # or the PubChem formula that disagrees with Wikidata.
    quality: dict[str, Any] = field(default_factory=dict)

    @property
    def elements(self) -> list[str]:
        return sorted(self.counts, key=lambda symbol: Z_BY_SYMBOL[symbol])

    @property
    def reduced(self) -> str | None:
        return reduced_formula(self.counts)

    @property
    def smiles(self) -> str | None:
        """PubChem SMILES, else Wikidata SMILES or a representative isomer."""
        value = self.pubchem.get("smiles") or self.wikidata_smiles
        return str(value) if value else None

    @property
    def mineral(self) -> bool:
        return CLASS_MINERAL_SPECIES in self.classes

    @property
    def single_atom(self) -> bool:
        return len(self.counts) == 1 and abs(next(iter(self.counts.values())) - 1) < 1e-6


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


def select_compounds(
    records: dict[str, wikidata.CompoundRecord],
    options: Options,
    *,
    excluded: frozenset[str] = frozenset(),
    electronegativity: dict[str, float] | None = None,
) -> list[Compound]:
    """Compounds for the dataset, most famous first.

    Skipped: chemical elements themselves, chemical groups (hydroxyl), single atoms and
    atomic ions (isotopes, H⁺, Fe³⁺: they belong to the element scene), unparseable or
    variable formulas, and giant formulas (proteins, antibodies: MAX_FORMULA_ATOMS).
    """
    selected: list[Compound] = []
    for record in records.values():
        if record.qid in excluded or not EXCLUDED_CLASSES.isdisjoint(record.classes):
            continue
        counts: ElementCounts | None = None
        raw_formula = ""
        for raw in sorted(record.formulas, key=lambda f: (len(f), f)):
            counts = parse_formula(raw)
            if counts:
                raw_formula = raw.strip()
                break
        if not counts or not record.articles or sum(counts.values()) > MAX_FORMULA_ATOMS:
            continue
        if options.only_elements and not set(counts) <= options.only_elements:
            continue
        compound = Compound(
            id=record.qid,
            formula=display_formula(raw_formula, counts, electronegativity or {}),
            counts=counts,
            names={language: capitalize(text) for language, text in record.labels.items() if text},
            articles=dict(record.articles),
            fame=record.sitelinks or len(record.articles),
            cid=min(record.cids) if record.cids else None,
            classes=sorted(record.classes),
            mp_hint=min(record.mp_ids) if record.mp_ids else None,
            charged=has_net_charge(raw_formula),
            wikidata_smiles=record.best_smiles or REPRESENTATIVE_SMILES.get(record.qid),
            image=min(record.images) if record.images else None,
        )
        if compound.single_atom and compound.id not in ALLOTROPE_STRUCTURES:
            continue
        selected.append(compound)
    selected.sort(key=lambda compound: (-compound.fame, compound.id))
    if options.limit:
        selected = selected[: options.limit]
    return selected


def prefers_crystal(compound: Compound, has_3d: bool) -> bool:
    """Ionic, metallic and network solids are shown as crystals, molecules as molecules."""
    if compound.id in ALLOTROPE_STRUCTURES or compound.mineral:
        return True
    if compound.charged:
        return False  # ions are drawn as molecules (NH₄⁺, SO₄²⁻)
    elements = set(compound.counts)
    if compound.reduced in NETWORK_SOLIDS:
        return True
    if len(elements) == 1:
        symbol = next(iter(elements))
        single_atom = abs(compound.counts[symbol] - 1) < 1e-6
        return single_atom and symbol not in MOLECULAR_ELEMENTS and symbol not in NOBLE_GASES and symbol != "C"
    has_metal = any(is_metal(symbol) for symbol in elements)
    smiles = compound.smiles or ""
    if has_metal and "C" not in elements:
        return True
    return "." in smiles and not has_3d


def _matches(structure: Structure, counts: ElementCounts) -> bool:
    found = composition(structure)
    if structure.get("kind") == "crystal":
        return same_proportions(found, counts)
    return set(found) == set(counts) and same_proportions(found, counts, tolerance=0.001)


def _same_counts(a: dict[str, int] | dict[str, float], b: ElementCounts) -> bool:
    return set(a) == set(b) and all(abs(a[key] - b[key]) < 1e-6 for key in a)


def molecular_crystal_matches(structure: Structure, counts: ElementCounts) -> bool:
    """For a molecule shown as a crystal: every bonded unit of the crystal must be this molecule.

    Ice (units H₂O) passes for water; solid H₂O₂ (units H₂O₂) fails for the OH radical,
    although both reduce to the formula 'HO'.
    """
    units: list[dict[str, int]] | None = structure.get("units")
    if not units:
        return False
    return all(_same_counts(unit, counts) for unit in units)


def structure_methods(compound: Compound, wants_crystal: bool) -> list[str]:
    """Structure sources to try, best first."""
    if wants_crystal:
        return ["crystal", "pubchem3d", "rdkit"]
    if compound.charged:
        return ["pubchem3d", "rdkit"]
    return ["pubchem3d", "rdkit", "crystal"]


PUBCHEM_3D_BUDGET_S = 40 * 60


EMBED_CHUNK = 25
MAX_POOL_RESTARTS = 20


RDKIT_MEMO = "rdkit-3d-v1"  # bump when molecule_from_smiles changes its output
EMBED_LOG_EVERY = 2000


def _remember_structure(fetcher: Fetcher, smiles: str, structure: Structure | None) -> None:
    """Memo of one RDKit result; a value that does not serialize is simply not remembered."""
    try:
        text = json.dumps(structure, default=lambda value: value.item() if hasattr(value, "item") else str(value))
        fetcher.memo_put(RDKIT_MEMO, smiles, text if structure else "")
    except (TypeError, ValueError, OSError) as error:
        log.debug("RDKit memo skipped for %s: %s", smiles, error)


def embed_all(smiles: list[str], fetcher: Fetcher | None = None) -> dict[str, Structure | None]:
    """RDKit 3D embedding in parallel processes (thousands of molecules).

    Embedding uses a fixed seed, so a SMILES always gives the same model: results are
    remembered per SMILES (fetcher memo) and the next build skips them. If RDKit
    crashes a worker process, the pool breaks: the chunk that was running is skipped
    (no 3D for those molecules) and a new pool continues with the rest.
    """
    if not smiles:
        return {}
    started = time.monotonic()
    results: dict[str, Structure | None] = {}
    if fetcher is not None:
        for item in smiles:
            remembered = fetcher.memo_get(RDKIT_MEMO, item)
            if remembered is not None:
                results[item] = json.loads(remembered) if remembered else None
    remaining = [item for item in smiles if item not in results]
    workers = max(1, (os.cpu_count() or 2))
    log.info("RDKit: %d molecules remembered, embedding %d on %d processes", len(results), len(remaining), workers)
    for _ in range(MAX_POOL_RESTARTS):
        if not remaining:
            break
        try:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                embedded = pool.map(molecule_from_smiles, remaining, chunksize=EMBED_CHUNK)
                for number, (item, structure) in enumerate(zip(remaining, embedded, strict=True), start=1):
                    results[item] = structure
                    if fetcher is not None:
                        _remember_structure(fetcher, item, structure)
                    if number % EMBED_LOG_EVERY == 0:
                        log.info("  RDKit: %d/%d (%.0f s)", number, len(remaining), time.monotonic() - started)
        except BrokenProcessPool:
            done = [item for item in remaining if item in results]
            skipped = [item for item in remaining if item not in results][:EMBED_CHUNK]
            log.warning("RDKit: a worker crashed; skipping %d molecules after %d done", len(skipped), len(done))
            results.update(dict.fromkeys(skipped))
        remaining = [item for item in remaining if item not in results]
    results.update(dict.fromkeys(remaining))
    log.info("RDKit: done in %.0f s", time.monotonic() - started)
    return results


@dataclass
class StructureResult:
    structure: Structure
    source: str
    ref: str | None
    origin: str | None = None  # crystals: "experimental" (ICSD) or "computed" (MP API, Q.2)


def assign_structures(
    compounds: list[Compound], fetcher: Fetcher, with_3d: list[int] | None = None
) -> tuple[dict[str, StructureResult], Counter[str]]:
    stats: Counter[str] = Counter()
    cids = [compound.cid for compound in compounds if compound.cid]

    # Ask for 3D only where PubChem has it (CIDs without properties are tried anyway).
    if with_3d is None:
        with_3d = [
            compound.cid
            for compound in compounds
            if compound.cid and int(compound.pubchem.get("conformers3d", 1) or 0) > 0
        ]
    log.info("PubChem 3D conformers for %d of %d CIDs", len(with_3d), len(cids))
    started = time.monotonic()
    conformers = pubchem.conformers_3d(fetcher, with_3d, budget_s=PUBCHEM_3D_BUDGET_S)
    log.info("PubChem 3D: %d records in %.0f s", len(conformers), time.monotonic() - started)
    stats["pubchem_3d_available"] = len(conformers)

    # RDKit for molecules (and salts) without a PubChem 3D record, on all CPU cores.
    smiles_jobs = sorted(
        {
            smiles
            for compound in compounds
            if (smiles := compound.smiles) and not (compound.cid and compound.cid in conformers)
        }
    )
    embedded = embed_all(smiles_jobs, fetcher)
    stats["rdkit_embedded"] = sum(1 for structure in embedded.values() if structure)

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
    # Q.2: which candidates match an experimental record (needs MP_API_KEY).
    origins = mp_api.origins(
        fetcher,
        [c.id for options in candidates.values() for c in options]
        + [compound.mp_hint for compound in compounds if compound.mp_hint]
        + list(ALLOTROPE_STRUCTURES.values()),
    )
    experimental = {identifier for identifier, origin in origins.items() if origin.experimental}
    stats["mp_api_origins"] = len(origins)
    chosen: dict[str, str] = {}
    for compound in compounds:
        if compound.id in ALLOTROPE_STRUCTURES:
            chosen[compound.id] = ALLOTROPE_STRUCTURES[compound.id]
        elif compound.mp_hint:
            chosen[compound.id] = compound.mp_hint
        elif compound.reduced and (best := optimade.best_candidate(candidates.get(compound.reduced, []), experimental)):
            chosen[compound.id] = best.id
    log.info("OPTIMADE structures for %d materials", len(set(chosen.values())))
    crystals = optimade.structures(fetcher, set(chosen.values()))

    log.info("Assigning structures for %d compounds", len(compounds))
    results: dict[str, StructureResult] = {}
    started = time.monotonic()
    for number, compound in enumerate(compounds, start=1):
        if number % 2000 == 0:
            log.info("  structures: %d/%d (%.0f s)", number, len(compounds), time.monotonic() - started)
        has_3d = bool(compound.cid and compound.cid in conformers)
        for method in structure_methods(compound, wants_crystal[compound.id]):
            structure: Structure | None = None
            ref: str | None = None
            if method == "pubchem3d" and has_3d and compound.cid:
                structure = parse_sdf(conformers[compound.cid])
                ref = str(compound.cid)
            elif method == "rdkit" and (smiles_text := compound.smiles):
                structure = embedded[smiles_text] if smiles_text in embedded else molecule_from_smiles(smiles_text)
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
            if (
                method == "crystal"
                and not wants_crystal[compound.id]
                and not molecular_crystal_matches(structure, compound.counts)
            ):
                stats["rejected_crystal_units"] += 1
                continue
            source = {"pubchem3d": "pubchem", "rdkit": "rdkit", "crystal": "materialsproject"}[method]
            origin = None
            if method == "crystal" and ref in origins:
                origin = "experimental" if origins[ref].experimental else "computed"
                stats[f"crystal_{origin}"] += 1
            results[compound.id] = StructureResult(structure=structure, source=source, ref=ref, origin=origin)
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
    origins = mp_api.origins(fetcher, [c.id for options in candidates.values() for c in options])
    experimental = {identifier for identifier, origin in origins.items() if origin.experimental}
    chosen = {
        symbol: best.id
        for symbol in crystal_symbols
        if (best := optimade.best_candidate(candidates.get(symbol, []), experimental))
    }
    chosen["C"] = "mp-48"  # graphite: the standard state of carbon
    crystals = optimade.structures(fetcher, set(chosen.values()))
    for element in elements:
        symbol = element["symbol"]
        if symbol in MOLECULAR_ELEMENTS:
            cid = MOLECULAR_ELEMENTS[symbol]
            if cid in molecular and (structure := parse_sdf(molecular[cid])):
                results[symbol] = StructureResult(structure, "pubchem", str(cid))
            elif structure := molecule_from_smiles(MOLECULAR_SMILES[symbol]):
                results[symbol] = StructureResult(structure, "rdkit", str(cid))
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
                origin = origins.get(chosen[symbol])
                mark = None if origin is None else ("experimental" if origin.experimental else "computed")
                results[symbol] = StructureResult(structure, "materialsproject", chosen[symbol], mark)
    return results


def fetch_descriptions(compounds: list[Compound], fetcher: Fetcher) -> None:
    for language in wikidata.LANGUAGES:
        by_title = {compound.articles[language]: compound for compound in compounds if language in compound.articles}
        log.info("Wikipedia %s extracts for %d articles", language, len(by_title))
        texts = wikipedia.extracts(fetcher, language, by_title)
        for title, text in texts.items():
            by_title[title].descriptions[language] = _trim(text)


def fetch_photos(
    compounds: list[Compound], elements: list[dict[str, Any]], element_images: dict[int, str], fetcher: Fetcher
) -> None:
    """Photos with author and license from Wikimedia Commons for compounds and elements."""
    names = [compound.image for compound in compounds if compound.image] + list(element_images.values())
    log.info("Commons photos for %d files", len(set(names)))
    found = commons.photos(fetcher, names)
    for compound in compounds:
        if compound.image and compound.image in found:
            compound.photo = found[compound.image].as_json()
    for element in elements:
        name = element_images.get(element["z"])
        if name and name in found:
            element["photo"] = found[name].as_json()


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
        **({"origin": result.origin} if result.origin else {}),
    }


def attach_pubchem(compounds: list[Compound], fetcher: Fetcher) -> list[int]:
    """PubChem properties (formula, mass, SMILES, InChIKey, IUPAC name) for compounds with a CID.

    Returns the CIDs to ask 3D for, as Wikidata links them: taken before the formula
    cross-check drops any link, they form the same 3D batches as earlier builds, and the
    URL cache serves them.
    """
    cids = [compound.cid for compound in compounds if compound.cid]
    log.info("PubChem properties for %d CIDs", len(cids))
    properties = pubchem.properties(fetcher, cids)
    for compound in compounds:
        if compound.cid and compound.cid in properties:
            compound.pubchem = properties[compound.cid]
    # CIDs without properties are tried anyway (default 1).
    return [cid for cid in cids if int(properties.get(cid, {}).get("conformers3d", 1) or 0) > 0]


QUALITY_EXAMPLES = 40
SHOWN_AS_IS = (Verdict.SCALED, Verdict.HYDRATE)  # report examples without a change to the card


@dataclass
class QualityReport:
    verdicts: Counter[str] = field(default_factory=Counter)
    examples: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))


def _formula_mass(compound: Compound, masses: dict[str, float]) -> float | None:
    """Mass from the formula, only where it means something: whole numbers, no isotopes."""
    if has_isotopes(compound.formula) or any(abs(value - round(value)) > 1e-6 for value in compound.counts.values()):
        return None
    return molar_mass(compound.counts, masses)


def reconcile_formulas(
    compounds: list[Compound],
    masses: dict[str, float],
    electronegativity: dict[str, float],
) -> QualityReport:
    """Cross-check Wikidata and PubChem formulas (Q.1) and settle the molar mass.

    Two sources that agree win over the third: the Wikidata SMILES (or an obvious "I"
    for "l" typo) decides between the Wikidata formula and the PubChem record.
    """
    report = QualityReport()
    for compound in compounds:
        check: FormulaCheck = check_formula(
            compound.formula, compound.counts, compound.pubchem.get("formula"), compound.wikidata_smiles
        )
        report.verdicts[check.verdict] += 1
        pubchem_mass = compound.pubchem.get("mass")
        note = ""
        if check.verdict in (Verdict.OK, Verdict.ISOTOPES) and pubchem_mass:
            compound.mass, compound.mass_source = float(pubchem_mass), "pubchem"
        elif check.verdict == Verdict.WIKIDATA_FIXED and check.pubchem:
            old = compound.formula
            compound.counts = dict(check.pubchem)
            compound.formula = to_subscripts(conventional_formula(compound.counts, electronegativity))
            compound.quality = {"wikidataFormula": old}
            if pubchem_mass:
                compound.mass, compound.mass_source = float(pubchem_mass), "pubchem"
            note = f"{old} → {compound.formula}"
        elif check.verdict == Verdict.PUBCHEM_DROPPED:
            compound.quality = {"pubchemDropped": compound.cid}
            note = f"CID {compound.cid}: {plain_formula(check.pubchem or {})}"
            compound.cid = None
            compound.pubchem = {}
        elif check.verdict == Verdict.DISAGREE and check.pubchem:
            # Keep the identity (Wikidata) and the PubChem link, but not PubChem's details:
            # they may describe another substance. The card shows both formulas.
            compound.quality = {"pubchemFormula": plain_formula(check.pubchem)}
            compound.pubchem = {"formula": compound.pubchem.get("formula")}
            note = f"PubChem CID {compound.cid}: {plain_formula(check.pubchem)}"
        if compound.mass is None and check.verdict != Verdict.DISAGREE:
            mass = _formula_mass(compound, masses)
            if mass is not None:
                compound.mass, compound.mass_source = mass, "formula"
        if note and len(report.examples[check.verdict]) < QUALITY_EXAMPLES:
            name = compound.names.get("en") or compound.names.get("ru") or ""
            report.examples[check.verdict].append(f"{compound.id} {compound.formula} — {name}: {note}")
        elif check.verdict in SHOWN_AS_IS and len(report.examples[check.verdict]) < QUALITY_EXAMPLES:
            report.examples[check.verdict].append(
                f"{compound.id} {compound.formula}: PubChem {plain_formula(check.pubchem or {})}"
            )
    log.info("Formula checks: %s", dict(report.verdicts))
    return report


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
        "mass": compound.mass,
        "massSource": compound.mass_source,
        "charge": net_charge(compound.formula),
        "smiles": compound.smiles,
        "inchikey": compound.pubchem.get("inchikey"),
        "iupac": compound.pubchem.get("iupac"),
        "classes": compound.classes,
        "structure": compound.structure,
        **({"photo": compound.photo} if compound.photo else {}),
        **({"quality": compound.quality} if compound.quality else {}),
    }


def _write_json(path: Path, data: Any) -> int:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


VERDICT_TITLES = {
    Verdict.OK: "совпадают",
    Verdict.NO_PUBCHEM: "нет записи PubChem",
    Verdict.ISOTOPES: "изотопы (D, T, ¹⁸F): верим PubChem",
    Verdict.SCALED: "те же пропорции, другой размер",
    Verdict.HYDRATE: "PubChem описывает гидрат или безводную форму — формула Wikidata, масса по ней",
    Verdict.WIKIDATA_FIXED: "ошибка в формуле Wikidata — исправлена",
    Verdict.PUBCHEM_DROPPED: "ссылка на PubChem ведёт к другому веществу — убрана",
    Verdict.DISAGREE: "расходятся, третьего мнения нет — показаны обе формулы",
}


def quality_lines(quality: QualityReport | None) -> list[str]:
    """Report section Q.4: how the Wikidata and PubChem formulas compare, with examples."""
    if quality is None or not quality.verdicts:
        return []
    lines = ["", "## Перекрёстная проверка формул (Wikidata, PubChem, SMILES)", ""]
    lines += ["| Итог | Соединений |", "| --- | --- |"]
    lines += [f"| {VERDICT_TITLES.get(Verdict(key), key)} | {count} |" for key, count in quality.verdicts.most_common()]
    for verdict in (Verdict.WIKIDATA_FIXED, Verdict.PUBCHEM_DROPPED, Verdict.DISAGREE, Verdict.HYDRATE, Verdict.SCALED):
        examples = quality.examples.get(verdict, [])
        if examples:
            lines += ["", f"### {VERDICT_TITLES[verdict]}", ""] + [f"- {line}" for line in examples]
    return lines


def write_report(
    root: Path,
    compounds: list[Compound],
    elements: list[dict[str, Any]],
    pairs: list[dict[str, Any]],
    stats: Counter[str],
    oversized: list[str],
    fetch_stats: Counter[str],
    seconds: float,
    classes: dict[str, dict[str, Any]] | None = None,
    neighbours: dict[str, list[tuple[str, float]]] | None = None,
    quality: QualityReport | None = None,
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
        f"- С фото: соединений {sum(1 for c in compounds if c.photo)}, "
        f"элементов {sum(1 for e in elements if e.get('photo'))}.",
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
    lines += quality_lines(quality)
    lines += ["", "## Запросы", "", "| Метрика | Значение |", "| --- | --- |"]
    lines += [f"| {key} | {value} |" for key, value in sorted(fetch_stats.items())]
    lines += ["", "## Топ-40 классов Wikidata", "", "| Класс | Название | Соединений |", "| --- | --- | --- |"]
    for qid, info in list((classes or {}).items())[:40]:
        names = info["names"]
        lines.append(f"| {qid} | {names.get('en') or names.get('ru') or '—'} | {info['count']} |")
    lines += ["", "## Векторная модель: ближайшие элементы", ""]
    for symbol, items in (neighbours or {}).items():
        lines.append(f"- {symbol}: " + ", ".join(f"{other} ({score})" for other, score in items))
    lines += ["", "## Топ-40 соединений", ""]
    for compound in compounds[:40]:
        kind = compound.structure["kind"] if compound.structure else "—"
        source = compound.structure["source"] if compound.structure else ""
        name = compound.names.get("ru") or compound.names.get("en") or ""
        lines.append(f"- {compound.formula} — {name} ({compound.fame} статей, {kind} {source})")
    (root / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(options: Options) -> Path:
    started = time.monotonic()
    root = options.out_dir / options.version
    (root / "structures").mkdir(parents=True, exist_ok=True)

    with Fetcher(options.cache_dir) as fetcher:
        log.info("Elements")
        element_labels = wikidata.fetch_element_labels(fetcher)
        elements = build_elements(pubchem.periodic_table(fetcher), element_labels)
        electronegativity = {e["symbol"]: e["electronegativity"] for e in elements if e["electronegativity"]}

        log.info("Compounds from Wikidata")
        compounds = select_compounds(
            wikidata.fetch_compounds(fetcher),
            options,
            excluded=frozenset(label.qid for label in element_labels.values()),
            electronegativity=electronegativity,
        )
        log.info("Selected %d compounds", len(compounds))

        log.info("Class labels")
        class_counts = Counter(qid for compound in compounds for qid in compound.classes)
        class_labels = wikidata.fetch_labels(fetcher, set(class_counts))
        classes = {
            qid: {"names": class_labels.get(qid, {}), "count": count} for qid, count in class_counts.most_common()
        }

        stats: Counter[str] = Counter()
        oversized: list[str] = []
        with_3d: list[int] | None = None
        if options.structures:
            with_3d = attach_pubchem(compounds, fetcher)
        masses = {element["symbol"]: element["mass"] for element in elements if element.get("mass")}
        quality = reconcile_formulas(compounds, masses, electronegativity)
        if options.structures:
            results, stats = assign_structures(compounds, fetcher, with_3d)
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
            fetch_photos(compounds, elements, wikidata.fetch_element_images(fetcher), fetcher)

        pairs = build_pairs(compounds)
        fetch_stats = fetcher.stats

    _write_json(root / "elements.json", elements)
    _write_json(root / "pairs.json", pairs)
    _write_json(root / "classes.json", classes)

    log.info("Vectors")
    element_vectors = embeddings.element_vectors([compound.counts for compound in compounds])
    compound_vectors = {
        compound.id: vector
        for compound in compounds
        if (vector := embeddings.compound_vector(compound.counts, element_vectors)) is not None
    }
    _write_json(
        root / "vectors.json",
        {
            "dim": embeddings.DIM,
            "method": "PPMI + SVD of element co-occurrence in compounds; compounds: atom-fraction mean",
            "elements": element_vectors,
            "compounds": compound_vectors,
        },
    )
    stats["vectors_elements"] = len(element_vectors)
    stats["vectors_compounds"] = len(compound_vectors)
    neighbours = {
        symbol: embeddings.nearest(element_vectors, symbol, 5) for symbol in ("Na", "Fe", "Cl", "C", "O", "U")
    }
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
    write_report(root, compounds, elements, pairs, stats, oversized, fetch_stats, seconds, classes, neighbours, quality)
    log.info("Dataset %s written in %.0f s", root, seconds)
    return root
