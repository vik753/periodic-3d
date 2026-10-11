"""Golden set (Q.3): reference substances whose facts we know for sure.

`p3d-pipeline verify <dataset>` checks a built dataset against this list: the record
exists, the formula, the molar mass (±0.3%), the kind of 3D model and, for crystals,
the shape of the unit cell. A failure means a source or a pipeline rule broke a
well-known substance; the data workflow then refuses to publish the dataset.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MASS_TOLERANCE = 0.003
LENGTH_TOLERANCE = 0.01
ANGLE_TOLERANCE_DEG = 1.0


@dataclass(frozen=True)
class Golden:
    qid: str
    name: str  # part of the English name
    hill: str
    mass: float | None  # g/mol
    kind: str  # molecule | crystal
    cell: str | None = None  # cubic | hexagonal (conventional cell of a crystal)


GOLDEN: tuple[Golden, ...] = (
    Golden("Q283", "Water", "H2O", 18.015, "molecule"),
    Golden("Q1997", "Carbon dioxide", "CO2", 44.009, "molecule"),
    Golden("Q37129", "Methane", "CH4", 16.043, "molecule"),
    Golden("Q153", "Ethanol", "C2H6O", 46.069, "molecule"),
    Golden("Q2270", "Benzene", "C6H6", 78.114, "molecule"),
    Golden("Q4087", "Ammonia", "H3N", 17.031, "molecule"),
    Golden("Q4118", "Sulfuric acid", "H2O4S", 98.072, "molecule"),
    Golden("Q60235", "Caffeine", "C8H10N4O2", 194.194, "molecule"),
    Golden("Q47512", "Acetic acid", "C2H4O2", 60.052, "molecule"),
    Golden("Q36933", "Ozone", "O3", 47.997, "molecule"),
    Golden("Q37525", "Glucose", "C6H12O6", 180.156, "molecule"),
    Golden("Q171877", "Hydrogen peroxide", "H2O2", 34.014, "molecule"),
    Golden("Q339940", "Sodium acetate", "C2H3NaO2", 82.034, "molecule"),
    Golden("Q2314", "Sodium chloride", "ClNa", 58.44, "crystal", "cubic"),
    Golden("Q5283", "Diamond", "C", 12.011, "crystal", "cubic"),
    Golden("Q5309", "Graphite", "C", 12.011, "crystal", "hexagonal"),
    Golden("Q103223", "Hematite", "Fe2O3", 159.687, "crystal", "hexagonal"),
    Golden("Q23767", "Calcium carbonate", "CCaO3", 100.086, "crystal", "hexagonal"),
    Golden("Q43010", "Quartz", "O2Si", 60.084, "crystal", "hexagonal"),
)


def _angle(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.hypot(*a) * math.hypot(*b)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / norm)))) if norm else 0.0


def cell_shape(cell: list[list[float]]) -> str:
    """'cubic', 'hexagonal' or 'other' for three lattice vectors."""
    lengths = [math.hypot(*vector) for vector in cell]
    angles = [_angle(cell[1], cell[2]), _angle(cell[0], cell[2]), _angle(cell[0], cell[1])]

    def close(x: float, y: float) -> bool:
        return abs(x - y) <= LENGTH_TOLERANCE * max(x, y)

    def right(angle: float) -> bool:
        return abs(angle - 90) <= ANGLE_TOLERANCE_DEG

    if all(right(angle) for angle in angles) and close(lengths[0], lengths[1]) and close(lengths[1], lengths[2]):
        return "cubic"
    for i, j, k in ((0, 1, 2), (0, 2, 1), (1, 2, 0)):
        between = _angle(cell[i], cell[j])
        others = [_angle(cell[i], cell[k]), _angle(cell[j], cell[k])]
        hexagonal = abs(between - 120) <= ANGLE_TOLERANCE_DEG or abs(between - 60) <= ANGLE_TOLERANCE_DEG
        if close(lengths[i], lengths[j]) and hexagonal and all(right(angle) for angle in others):
            return "hexagonal"
    return "other"


def check(golden: Golden, card: dict[str, Any] | None, structure: dict[str, Any] | None) -> list[str]:
    """Problems with one reference substance; an empty list means it is right."""
    if card is None:
        return [f"{golden.qid} {golden.name}: missing from the dataset"]
    problems: list[str] = []
    label = f"{golden.qid} {golden.name}"
    if golden.name.lower() not in str(card.get("names", {}).get("en", "")).lower():
        problems.append(f"{label}: English name is {card.get('names', {}).get('en')!r}")
    if card.get("hill") != golden.hill:
        problems.append(f"{label}: formula {card.get('hill')} instead of {golden.hill}")
    mass = card.get("mass")
    if golden.mass is not None:
        if mass is None:
            problems.append(f"{label}: no molar mass")
        elif abs(float(mass) - golden.mass) > MASS_TOLERANCE * golden.mass:
            problems.append(f"{label}: molar mass {mass} instead of {golden.mass}")
    kind = (card.get("structure") or {}).get("kind")
    if kind != golden.kind:
        problems.append(f"{label}: 3D model is {kind!r} instead of {golden.kind!r}")
    if golden.cell:
        cell = (structure or {}).get("cell")
        shape = cell_shape(cell) if cell else "none"
        if shape != golden.cell:
            problems.append(f"{label}: unit cell is {shape} instead of {golden.cell}")
    return problems


def verify(root: Path) -> list[str]:
    """Check a dataset directory (with compounds.jsonl and structures/) against GOLDEN."""
    wanted = {golden.qid for golden in GOLDEN}
    cards: dict[str, dict[str, Any]] = {}
    with (root / "compounds.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                card = json.loads(line)
                if card["id"] in wanted:
                    cards[card["id"]] = card
    problems: list[str] = []
    for golden in GOLDEN:
        path = root / "structures" / f"{golden.qid}.json"
        structure = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
        problems += check(golden, cards.get(golden.qid), structure)
    return problems
