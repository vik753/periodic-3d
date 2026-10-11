"""Cross-checks between sources (Q.1): Wikidata formula, PubChem formula, Wikidata SMILES.

People edit Wikidata and Wikipedia, and sometimes make mistakes: "KCIO₃" (carbon and
iodine) for potassium chlorate, a nerve agent without its phosphorus, a PubChem link
that points to the anhydrous salt instead of the hydrate. Three independent records
describe each compound: the Wikidata formula, the PubChem record linked from Wikidata
and the Wikidata SMILES. When two of them agree, the third one is the error.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from .chemistry import is_metal
from .formula import ElementCounts, parse_formula, same_proportions

# Deuterium, tritium or an isotope mass number (²H, ¹⁸F) in the formula.
_ISOTOPE = re.compile(r"[DT](?![a-z])|[⁰¹²³⁴⁵⁶⁷⁸⁹]+[A-Z]")


class Verdict(StrEnum):
    OK = "ok"  # Wikidata and PubChem formulas agree
    NO_PUBCHEM = "no_pubchem"  # nothing to compare with
    ISOTOPES = "isotopes"  # D₂O, ¹⁸F: PubChem counts isotopes its own way; trust it
    SCALED = "scaled"  # same proportions, other size (a dimer record, a formula unit)
    HYDRATE = "hydrate"  # PubChem has the hydrate or the anhydrous form: keep Wikidata's
    WIKIDATA_FIXED = "wikidata_fixed"  # SMILES agrees with PubChem: the Wikidata formula was wrong
    PUBCHEM_DROPPED = "pubchem_dropped"  # SMILES agrees with Wikidata: the PubChem link was wrong
    DISAGREE = "disagree"  # no third opinion: show the conflict, drop PubChem details


@dataclass(frozen=True)
class FormulaCheck:
    verdict: Verdict
    pubchem: ElementCounts | None = None
    smiles: ElementCounts | None = None


def has_isotopes(formula: str) -> bool:
    return bool(_ISOTOPE.search(formula))


def same_counts(a: ElementCounts, b: ElementCounts) -> bool:
    return set(a) == set(b) and all(abs(a[key] - b[key]) < 1e-6 for key in a)


def formula_from_smiles(smiles: str | None) -> ElementCounts | None:
    """Element counts of a SMILES with implicit hydrogens (RDKit); None if it does not parse."""
    if not smiles:
        return None
    try:
        from rdkit import Chem, RDLogger
        from rdkit.Chem import rdMolDescriptors

        RDLogger.DisableLog("rdApp.*")
        molecule = Chem.MolFromSmiles(smiles)
        if molecule is None:
            return None
        return parse_formula(rdMolDescriptors.CalcMolFormula(molecule))
    except Exception:  # a bad SMILES must not stop the build
        return None


def water_difference(a: ElementCounts, b: ElementCounts) -> float | None:
    """n when a and b differ by exactly n water molecules (n ≠ 0), else None."""
    keys = set(a) | set(b)
    delta = {key: a.get(key, 0.0) - b.get(key, 0.0) for key in keys}
    n = delta.get("O", 0.0)
    if abs(n) < 1e-6 or abs(n - round(n)) > 1e-6:
        return None
    if abs(delta.get("H", 0.0) - 2 * n) > 1e-6:
        return None
    if any(abs(value) > 1e-6 for key, value in delta.items() if key not in ("H", "O")):
        return None
    return n


def plausible_fix(wikidata: ElementCounts, pubchem: ElementCounts) -> bool:
    """May PubChem's formula replace Wikidata's when the Wikidata SMILES backs PubChem?

    Wikidata SMILES are often copied from PubChem, so "two sources agree" is weaker
    than it looks. PubChem also writes salts, ions and complexes its own way: a dye
    without its chloride (rhodamine 6G), acetylacetonate with protonated ligands,
    inorganic species with extra hydrogens (UC → CH₄U). The fix is taken only for plain
    organic molecules, when no element disappears, and when the hydrogen count differs
    by more than one (±1 H is usually a charge or radical form, not an error).
    """
    elements = set(wikidata) | set(pubchem)
    if not {"C", "H"} <= set(wikidata) or not {"C", "H"} <= set(pubchem):
        return False
    if any(is_metal(symbol) for symbol in elements):
        return False
    if not set(wikidata) <= set(pubchem):
        return False
    others = [key for key in elements if key != "H" and abs(wikidata.get(key, 0) - pubchem.get(key, 0)) > 1e-6]
    hydrogen = abs(wikidata.get("H", 0) - pubchem.get("H", 0))
    return bool(others) or hydrogen >= 2 - 1e-6


def check_formula(
    formula: str,
    counts: ElementCounts,
    pubchem_formula: str | None,
    smiles: str | None,
) -> FormulaCheck:
    """Compare the Wikidata formula with PubChem; ask the Wikidata SMILES when they differ."""
    pubchem = parse_formula(pubchem_formula) if pubchem_formula else None
    if pubchem is None:
        return FormulaCheck(Verdict.NO_PUBCHEM)
    if same_counts(pubchem, counts):
        return FormulaCheck(Verdict.OK, pubchem)
    if has_isotopes(formula):
        return FormulaCheck(Verdict.ISOTOPES, pubchem)
    if same_proportions(pubchem, counts, tolerance=0.001):
        return FormulaCheck(Verdict.SCALED, pubchem)
    if water_difference(pubchem, counts) is not None:
        return FormulaCheck(Verdict.HYDRATE, pubchem)
    if any(same_counts(variant, pubchem) for variant in typo_variants(formula)):
        return FormulaCheck(Verdict.WIKIDATA_FIXED, pubchem)
    from_smiles = formula_from_smiles(smiles)
    if from_smiles is not None:
        if same_proportions(from_smiles, pubchem, tolerance=0.001) and plausible_fix(counts, pubchem):
            return FormulaCheck(Verdict.WIKIDATA_FIXED, pubchem, from_smiles)
        if same_proportions(from_smiles, counts, tolerance=0.001):
            return FormulaCheck(Verdict.PUBCHEM_DROPPED, pubchem, from_smiles)
    return FormulaCheck(Verdict.DISAGREE, pubchem, from_smiles)


_UPPER_I = re.compile(r"(?<=[A-Z])I")


def typo_variants(formula: str) -> list[ElementCounts]:
    """Readings of a formula with a capital I typed for l or i: "KCIO₃" → KClO₃, "SIO₂" → SiO₂.

    Fonts without serifs draw I and l alike, so this typo survives in sources.
    """
    variants: list[ElementCounts] = []
    for match in _UPPER_I.finditer(formula):
        for letter in ("l", "i"):
            text = formula[: match.start()] + letter + formula[match.end() :]
            counts = parse_formula(text)
            if counts:
                variants.append(counts)
    return variants


def molar_mass(counts: ElementCounts, masses: dict[str, float]) -> float | None:
    """Molar mass from the formula, g/mol; None when an element has no standard mass."""
    total = 0.0
    for symbol, amount in counts.items():
        mass = masses.get(symbol)
        if mass is None:
            return None
        total += mass * amount
    return round(total, 3) if total > 0 else None


def plain_formula(counts: ElementCounts) -> str:
    """Hill-order ASCII formula for reports: C first, then H, then the rest alphabetically."""
    order = (["C", "H"] if "C" in counts else []) + sorted(
        symbol for symbol in counts if "C" not in counts or symbol not in ("C", "H")
    )
    parts = []
    for symbol in order:
        if symbol not in counts:
            continue
        amount = counts[symbol]
        text = "" if abs(amount - 1) < 1e-6 else (f"{amount:g}")
        parts.append(f"{symbol}{text}")
    return "".join(parts)
