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
from typing import Any

import numpy as np

from .chemistry import NONMETALS, covalent_radius
from .elements_table import SYMBOLS, Z_BY_SYMBOL

Structure = dict[str, Any]

MAX_CRYSTAL_ATOMS = 160
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


def molecule_from_smiles(smiles: str, *, seed: int = 42, max_atoms: int = 400) -> Structure | None:
    """Embed a single-fragment molecule in 3D with RDKit (ETKDG + force field).

    Falls back to a flat 2D layout when 3D embedding fails. Returns None for
    multi-fragment SMILES (salts) and when RDKit cannot parse the input.
    """
    try:
        from rdkit import Chem, RDLogger
        from rdkit.Chem import AllChem
    except ImportError:
        return None
    RDLogger.DisableLog("rdApp.*")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None or len(Chem.GetMolFrags(mol)) > 1:
        return None
    mol = Chem.AddHs(mol)
    if mol.GetNumAtoms() > max_atoms:
        return None
    kind = "molecule"
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    if AllChem.EmbedMolecule(mol, params) != 0:
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
    return {"kind": kind, "atoms": atoms, "bonds": bonds}


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


def crystal_fragment(
    lattice_vectors: list[list[float]],
    cartesian_positions: list[list[float]],
    species: list[str],
    *,
    max_atoms: int = MAX_CRYSTAL_ATOMS,
) -> Structure | None:
    """Unit cell for display: standardized, closed with boundary images, with bonds."""
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

    points = _with_boundary_images(frac)
    if len(points) > max_atoms * 1.6:
        points = [(point, index) for index, point in enumerate(np.mod(frac, 1.0))]
    positions = np.array([point for point, _ in points]) @ lattice
    elements = [SYMBOLS[numbers[index] - 1] for _, index in points]
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
