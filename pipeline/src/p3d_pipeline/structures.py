"""3D structures for the viewer.

Output shape (shared with the frontend, see apps/web/src/data/structure.ts):
    {"kind": "molecule" | "crystal" | "flat",
     "atoms": [{"el": "O", "x": 0.0, "y": 0.0, "z": 0.0}, ...],
     "bonds": [[a, b, order], ...],
     "cell": [[ax, ay, az], [bx, by, bz], [cx, cy, cz]],   # crystals only
     "cellOrigin": [0, 0, 0]}                              # crystals only
"""

from __future__ import annotations

import contextlib
import itertools
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np

from .chemistry import NONMETALS, covalent_radius
from .elements_table import SYMBOLS, Z_BY_SYMBOL

Structure = dict[str, Any]

MAX_CRYSTAL_ATOMS = 160
MAX_3D_HEAVY_ATOMS = 150  # bigger molecules get a flat layout: embedding is slow and the 3D view is cluttered
EMBED_TIMEOUT_S = 20
MAX_BONDS_PER_ATOM = 12
MAX_UNIT_ATOMS = 240
SYMPREC_STEPS = (0.1, 0.01, 1e-3)


def _r(value: float) -> float:
    return round(float(value), 3)


# ---------------------------------------------------------------------------
# Molecules
# ---------------------------------------------------------------------------


def parse_sdf(record: str) -> Structure | None:
    """Parse one V2000 molfile record (as PubChem returns) into a structure."""
    lines = record.splitlines()
    if len(lines) < 4 or "V3000" in lines[3]:
        return None
    try:
        n_atoms = int(lines[3][0:3])
        n_bonds = int(lines[3][3:6])
    except ValueError:
        return None
    atoms = []
    for line in lines[4 : 4 + n_atoms]:
        try:
            x, y, z = float(line[0:10]), float(line[10:20]), float(line[20:30])
        except ValueError:
            return None
        element = line[31:34].strip()
        if element in ("D", "T"):
            element = "H"
        atoms.append({"el": element, "x": _r(x), "y": _r(y), "z": _r(z)})
    bonds = []
    for line in lines[4 + n_atoms : 4 + n_atoms + n_bonds]:
        try:
            a, b, kind = int(line[0:3]) - 1, int(line[3:6]) - 1, int(line[6:9])
        except ValueError:
            return None
        bonds.append([a, b, {1: 1, 2: 2, 3: 3, 4: 1.5}.get(kind, 1)])
    if len(atoms) != n_atoms:
        return None
    return {"kind": "molecule", "atoms": atoms, "bonds": bonds}


MAX_FRAGMENTS = 16
ION_GAP = 2.5  # Å from a counter-ion to the oppositely charged atom it sits next to
NEUTRAL_GAP = 2.9  # Å for neutral parts (water of crystallization)


@dataclass
class Fragment:
    """One embedded part of a multi-part SMILES (an ion or a water molecule)."""

    structure: Structure
    charges: list[int]  # formal charge per atom


def _fibonacci_sphere(count: int) -> np.ndarray:
    """Evenly spread unit vectors (directions to try when placing a fragment)."""
    index = np.arange(count) + 0.5
    polar = np.arccos(1 - 2 * index / count)
    azimuth = np.pi * (1 + 5**0.5) * index
    return np.column_stack([np.cos(azimuth) * np.sin(polar), np.sin(azimuth) * np.sin(polar), np.cos(polar)])


_DIRECTIONS = _fibonacci_sphere(96)


def _coordinates(structure: Structure) -> np.ndarray:
    return np.array([[atom["x"], atom["y"], atom["z"]] for atom in structure["atoms"]], dtype=float).reshape(-1, 3)


def assemble_fragments(fragments: list[Fragment]) -> Structure:
    """Place the parts of a salt or hydrate next to each other.

    The largest part stays at the centre. Every other part touches a free atom of the
    opposite charge (Na⁺ next to O⁻ of acetate) or, when neutral, an O or N atom.
    Among 96 directions the one with the most room wins, so parts do not overlap.
    """
    order = sorted(range(len(fragments)), key=lambda i: (-len(fragments[i].structure["atoms"]), i))
    first = fragments[order[0]]
    placed = _coordinates(first.structure)
    placed -= placed.mean(axis=0)
    elements = [atom["el"] for atom in first.structure["atoms"]]
    bonds = [list(bond) for bond in first.structure["bonds"]]
    charges = list(first.charges)
    flat = first.structure["kind"] == "flat"
    used: Counter[int] = Counter()
    for index in order[1:]:
        fragment = fragments[index]
        local = _coordinates(fragment.structure)
        charge = sum(fragment.charges)
        centre = local.mean(axis=0)
        charged = [i for i, value in enumerate(fragment.charges) if value]
        heavy = [i for i, atom in enumerate(fragment.structure["atoms"]) if atom["el"] != "H"] or [0]
        contact = min(charged or heavy, key=lambda i: float(np.linalg.norm(local[i] - centre)))
        local = local - local[contact]
        anchors = [i for i, value in enumerate(charges) if charge and value * charge < 0]
        if not anchors:
            anchors = [i for i, symbol in enumerate(elements) if symbol in ("O", "N")]
        if not anchors:
            anchors = [i for i, symbol in enumerate(elements) if symbol != "H"] or [0]
        anchor = min(anchors, key=lambda i: (used[i], i))
        used[anchor] += 1
        outward = placed[anchor] - placed.mean(axis=0)
        norm = float(np.linalg.norm(outward))
        outward = outward / norm if norm > 1e-6 else np.array([1.0, 0.0, 0.0])
        gap = ION_GAP if charge else NEUTRAL_GAP
        best_score, best = -np.inf, local + placed[anchor] + gap * _DIRECTIONS[0]
        for direction in _DIRECTIONS:
            moved = local + placed[anchor] + gap * direction
            clearance = float(np.min(np.linalg.norm(moved[:, None, :] - placed[None, :, :], axis=2)))
            score = min(clearance, gap) + 0.5 * float(direction @ outward)
            if score > best_score:
                best_score, best = score, moved
        offset = len(elements)
        bonds += [[a + offset, b + offset, kind] for a, b, kind in fragment.structure["bonds"]]
        elements += [atom["el"] for atom in fragment.structure["atoms"]]
        charges += fragment.charges
        placed = np.vstack([placed, best])
        flat = flat or fragment.structure["kind"] == "flat"
    placed -= placed.mean(axis=0)
    atoms = [
        {"el": symbol, "x": _r(x), "y": _r(y), "z": _r(z)} for symbol, (x, y, z) in zip(elements, placed, strict=True)
    ]
    return {"kind": "flat" if flat else "molecule", "atoms": atoms, "bonds": bonds}


def molecule_from_smiles(smiles: str, *, seed: int = 42, max_atoms: int = 400) -> Structure | None:
    """Embed a molecule in 3D with RDKit (ETKDG + force field).

    Salts and hydrates (multi-part SMILES, "CC(=O)[O-].[Na+]") are embedded part by
    part and placed side by side (assemble_fragments). Falls back to a flat 2D layout
    when 3D embedding fails. Returns None when RDKit cannot parse the input.
    """
    try:
        from rdkit import Chem, RDLogger
    except ImportError:
        return None
    RDLogger.DisableLog("rdApp.*")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    parts = Chem.GetMolFrags(mol, asMols=True)
    if len(parts) > MAX_FRAGMENTS:
        return None
    fragments: list[Fragment] = []
    budget = max_atoms
    for part in parts:
        fragment = _embed(part, seed=seed, max_atoms=budget)
        if fragment is None:
            return None
        budget -= len(fragment.structure["atoms"])
        fragments.append(fragment)
    if len(fragments) == 1:
        return fragments[0].structure
    return assemble_fragments(fragments)


def _embed(mol: Any, *, seed: int, max_atoms: int) -> Fragment | None:
    """3D coordinates for one connected molecule (RDKit Mol)."""
    from rdkit import Chem
    from rdkit.Chem import AllChem

    heavy_atoms = mol.GetNumAtoms()
    mol = Chem.AddHs(mol)
    if mol.GetNumAtoms() > max_atoms:
        return None
    if mol.GetNumAtoms() == 1:
        atom = mol.GetAtomWithIdx(0)
        point = {"el": atom.GetSymbol(), "x": 0.0, "y": 0.0, "z": 0.0}
        return Fragment({"kind": "molecule", "atoms": [point], "bonds": []}, [atom.GetFormalCharge()])
    kind = "molecule"
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    with contextlib.suppress(AttributeError):
        params.timeout = EMBED_TIMEOUT_S  # RDKit ≥ 2023.09; keeps rare hard cases from stalling the build
    if heavy_atoms > MAX_3D_HEAVY_ATOMS:
        AllChem.Compute2DCoords(mol)
        kind = "flat"
    elif AllChem.EmbedMolecule(mol, params) != 0:
        params.useRandomCoords = True
        if AllChem.EmbedMolecule(mol, params) != 0:
            AllChem.Compute2DCoords(mol)
            kind = "flat"
    if kind == "molecule":
        try:
            if AllChem.MMFFHasAllMoleculeParams(mol):
                AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
            else:
                AllChem.UFFOptimizeMolecule(mol, maxIters=500)
        except Exception:
            pass
    with contextlib.suppress(Exception):  # keep aromatic orders if kekulization fails
        Chem.Kekulize(mol, clearAromaticFlags=True)
    conformer = mol.GetConformer()
    atoms = []
    for atom in mol.GetAtoms():
        position = conformer.GetAtomPosition(atom.GetIdx())
        atoms.append({"el": atom.GetSymbol(), "x": _r(position.x), "y": _r(position.y), "z": _r(position.z)})
    bonds = [[bond.GetBeginAtomIdx(), bond.GetEndAtomIdx(), bond.GetBondTypeAsDouble() or 1] for bond in mol.GetBonds()]
    charges = [atom.GetFormalCharge() for atom in mol.GetAtoms()]
    return Fragment({"kind": kind, "atoms": atoms, "bonds": bonds}, charges)


# ---------------------------------------------------------------------------
# Crystals
# ---------------------------------------------------------------------------

_SPECIES_SYMBOL = re.compile(r"[A-Z][a-z]?")


def _species_symbol(name: str) -> str | None:
    match = _SPECIES_SYMBOL.match(name)
    if not match:
        return None
    symbol = match.group()
    return symbol if symbol in Z_BY_SYMBOL else None


def _standardize(
    lattice: np.ndarray, frac: np.ndarray, numbers: list[int], max_atoms: int
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """Conventional standard cell via spglib; the primitive cell if the conventional one is too big."""
    try:
        import spglib
    except ImportError:
        return lattice, frac, numbers
    cell = (lattice.tolist(), frac.tolist(), numbers)
    # Computed structures carry small distortions (magnetic order, relaxation noise).
    # A loose tolerance recovers the textbook symmetry: bcc iron, corundum-type hematite.
    for symprec in SYMPREC_STEPS:
        for to_primitive in (False, True):
            try:
                result = spglib.standardize_cell(cell, to_primitive=to_primitive, no_idealize=False, symprec=symprec)
            except Exception:
                result = None
            if result is None:
                continue
            new_lattice, new_frac, new_numbers = result
            if len(new_numbers) <= max_atoms:
                return np.asarray(new_lattice, float), np.asarray(new_frac, float), [int(n) for n in new_numbers]
    return lattice, frac, numbers


def _with_boundary_images(frac: np.ndarray, eps: float = 1e-3) -> list[tuple[np.ndarray, int]]:
    """Atoms of the cell plus their copies on the far faces, so the cell looks closed."""
    wrapped = np.mod(frac, 1.0)
    wrapped[wrapped > 1 - eps] = 0.0
    points: list[tuple[np.ndarray, int]] = []
    for index, point in enumerate(wrapped):
        axes = [(0, 1) if point[k] < eps else (0,) for k in range(3)]
        for shift in itertools.product(*axes):
            points.append((point + np.array(shift, float), index))
    return points


def _bond_cutoffs(elements: list[str]) -> np.ndarray:
    """Pairwise maximum bond lengths; 0 where no bond is drawn (metal–metal next to anions)."""
    nonmetal = np.array([element in NONMETALS for element in elements])
    radii = np.array([covalent_radius(element) for element in elements])
    both_nonmetal = nonmetal[:, None] & nonmetal[None, :]
    both_metal = ~nonmetal[:, None] & ~nonmetal[None, :]
    tolerance = np.where(both_nonmetal, 1.1, 1.2)
    cutoffs = (radii[:, None] + radii[None, :]) * tolerance
    if nonmetal.any():
        cutoffs = np.where(both_metal, 0.0, cutoffs)
    return np.asarray(cutoffs, float)


def crystal_bonds(cart: np.ndarray, elements: list[str]) -> list[list[float]]:
    """Distance-based bonds. Metal–metal bonds are skipped in compounds with anions."""
    count = len(elements)
    if count < 2:
        return []
    cutoffs = _bond_cutoffs(elements)
    deltas = cart[:, None, :] - cart[None, :, :]
    distances = np.sqrt((deltas**2).sum(axis=-1))
    candidates: list[tuple[float, int, int]] = []
    for i in range(count):
        for j in range(i + 1, count):
            distance = float(distances[i, j])
            if 0.4 < distance <= cutoffs[i, j]:
                candidates.append((distance, i, j))
    candidates.sort()
    degree: Counter[int] = Counter()
    bonds: list[list[float]] = []
    for _, i, j in candidates:
        if degree[i] >= MAX_BONDS_PER_ATOM or degree[j] >= MAX_BONDS_PER_ATOM:
            continue
        degree[i] += 1
        degree[j] += 1
        bonds.append([i, j, 1])
    return bonds


SMALL_CELL_SITES = 8
SUPERCELL_TARGET = 6.0  # Å: a block of cells should be at least this long on each side
SUPERCELL_MAX_SITES = 64


def supercell_repeats(lattice: np.ndarray, sites: int) -> tuple[int, int, int]:
    """How many cells to show along a, b, c: more than one only for tiny cells."""
    if sites >= SMALL_CELL_SITES:
        return (1, 1, 1)
    lengths = np.linalg.norm(lattice, axis=1)
    target = max(SUPERCELL_TARGET, float(lengths.max()))
    repeats = [int(min(3, max(1, round(target / float(length))))) for length in lengths]
    while sites * repeats[0] * repeats[1] * repeats[2] > SUPERCELL_MAX_SITES:
        largest = repeats.index(max(repeats))
        repeats[largest] -= 1
    return (repeats[0], repeats[1], repeats[2])


def crystal_fragment(
    lattice_vectors: list[list[float]],
    cartesian_positions: list[list[float]],
    species: list[str],
    *,
    max_atoms: int = MAX_CRYSTAL_ATOMS,
) -> Structure | None:
    """Unit cell for display: standardized, closed with boundary images, with bonds.

    The frame ("cell") always shows one unit cell; tiny cells are repeated around it
    (supercell_repeats), so metals and graphite look like a crystal, not a few balls.
    """
    lattice = np.asarray(lattice_vectors, float)
    cart = np.asarray(cartesian_positions, float)
    if lattice.shape != (3, 3) or cart.ndim != 2 or len(cart) == 0 or len(cart) != len(species):
        return None
    symbols = [_species_symbol(name) for name in species]
    if any(symbol is None for symbol in symbols):
        return None
    numbers = [Z_BY_SYMBOL[symbol] for symbol in symbols if symbol]
    frac = np.linalg.solve(lattice.T, cart.T).T
    lattice, frac, numbers = _standardize(lattice, np.mod(frac, 1.0), numbers, max_atoms)

    # Tiny cells (iron: 2 atoms, graphite: 4) are shown as a block of a few cells.
    repeats = supercell_repeats(lattice, len(numbers))
    shifts = np.array(list(itertools.product(*(range(n) for n in repeats))), dtype=float)
    super_frac = ((np.mod(frac, 1.0)[None, :, :] + shifts[:, None, :]) / np.array(repeats, float)).reshape(-1, 3)
    super_numbers = numbers * len(shifts)
    super_lattice = lattice * np.array(repeats, float)[:, None]

    points = _with_boundary_images(super_frac)
    if len(points) > max_atoms * 1.6:
        points = [(point, index) for index, point in enumerate(np.mod(super_frac, 1.0))]
    positions = np.array([point for point, _ in points]) @ super_lattice
    elements = [SYMBOLS[super_numbers[index] - 1] for _, index in points]
    atoms = [
        {"el": element, "x": _r(position[0]), "y": _r(position[1]), "z": _r(position[2])}
        for element, position in zip(elements, positions, strict=True)
    ]
    return {
        "kind": "crystal",
        "atoms": atoms,
        "bonds": crystal_bonds(positions, elements),
        "cell": [[_r(v) for v in row] for row in lattice],
        "cellOrigin": [0, 0, 0],
        "sites": Counter(SYMBOLS[n - 1] for n in numbers),
        "units": molecular_units(lattice, frac, numbers),
    }


_SHIFTS = np.array(list(itertools.product((-1, 0, 1), repeat=3)), dtype=int)


def molecular_units(lattice: np.ndarray, frac: np.ndarray, numbers: list[int]) -> list[dict[str, int]] | None:
    """Compositions of the bonded units of a periodic structure.

    Ice gives [{'H': 2, 'O': 1}, ...]: separate molecules. Returns None for extended
    networks (quartz, metals, salts), where a bonded unit meets its own periodic image.
    """
    count = len(numbers)
    if count == 0 or count > MAX_UNIT_ATOMS:
        return None
    elements = [SYMBOLS[number - 1] for number in numbers]
    cutoffs = _bond_cutoffs(elements)
    deltas = np.mod(frac, 1.0)[None, :, :] - np.mod(frac, 1.0)[:, None, :]  # j − i
    # distances[s, i, j]: from atom i to the image of atom j shifted by _SHIFTS[s]
    cart = (deltas[None, :, :, :] + _SHIFTS[:, None, None, :]) @ lattice
    distances = np.sqrt((cart**2).sum(axis=-1))
    bonded = (distances > 0.4) & (distances <= cutoffs[None, :, :])
    neighbours: list[list[tuple[int, tuple[int, int, int]]]] = [[] for _ in range(count)]
    for s, i, j in zip(*np.nonzero(bonded), strict=True):
        shift = _SHIFTS[s]
        neighbours[int(i)].append((int(j), (int(shift[0]), int(shift[1]), int(shift[2]))))

    offsets: dict[int, tuple[int, int, int]] = {}
    units: list[dict[str, int]] = []
    for start in range(count):
        if start in offsets:
            continue
        offsets[start] = (0, 0, 0)
        stack = [start]
        unit: Counter[str] = Counter()
        while stack:
            atom = stack.pop()
            unit[elements[atom]] += 1
            ox, oy, oz = offsets[atom]
            for other, (sx, sy, sz) in neighbours[atom]:
                target = (ox + sx, oy + sy, oz + sz)
                if other not in offsets:
                    offsets[other] = target
                    stack.append(other)
                elif offsets[other] != target:
                    return None  # the unit reaches its own image: an extended network
        units.append(dict(unit))
    return units


def composition(structure: Structure) -> dict[str, float]:
    """Element counts of a structure (crystal: counts of unique cell sites)."""
    if structure.get("kind") == "crystal" and "sites" in structure:
        return {k: float(v) for k, v in structure["sites"].items()}
    counts: Counter[str] = Counter(atom["el"] for atom in structure.get("atoms", []))
    return {k: float(v) for k, v in counts.items()}


def finalize(structure: Structure) -> Structure:
    """Drop helper fields before writing to disk."""
    return {key: value for key, value in structure.items() if key not in ("sites", "units")}
