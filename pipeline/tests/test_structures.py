import importlib.util

import numpy as np
import pytest

from p3d_pipeline.formula import same_proportions
from p3d_pipeline.structures import (
    ION_GAP,
    Fragment,
    assemble_fragments,
    composition,
    crystal_fragment,
    molecular_units,
    molecule_from_smiles,
    parse_sdf,
    supercell_repeats,
)

WATER_SDF = """962
  -OEChem-10102618053D

  3  2  0     0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    0.2774    0.8929    0.2544 H   0  0  0  0  0  0  0  0  0  0  0  0
    0.6068   -0.2383   -0.7169 H   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0  0  0  0
  1  3  1  0  0  0  0
M  END
> <PUBCHEM_COMPOUND_CID>
962

"""


def test_parse_sdf_water() -> None:
    structure = parse_sdf(WATER_SDF)
    assert structure is not None
    assert structure["kind"] == "molecule"
    assert [atom["el"] for atom in structure["atoms"]] == ["O", "H", "H"]
    assert structure["bonds"] == [[0, 1, 1], [0, 2, 1]]
    assert composition(structure) == {"O": 1.0, "H": 2.0}


def test_parse_sdf_rejects_garbage() -> None:
    assert parse_sdf("not a molfile") is None


def test_rock_salt_fragment_from_conventional_cell() -> None:
    a = 5.64
    lattice = [[a, 0, 0], [0, a, 0], [0, 0, a]]
    na = [[0, 0, 0], [0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0]]
    cl = [[0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5], [0.5, 0.5, 0.5]]
    cart = [[x * a, y * a, z * a] for x, y, z in na + cl]
    structure = crystal_fragment(lattice, cart, ["Na"] * 4 + ["Cl"] * 4)
    assert structure is not None
    assert structure["kind"] == "crystal"
    # 4 + 4 sites, closed with boundary images: the classic 27-atom cube (14 Na + 13 Cl).
    assert len(structure["atoms"]) == 27
    assert same_proportions(composition(structure), {"Na": 1, "Cl": 1})
    # Only Na–Cl bonds (no metal–metal bonds in an ionic crystal).
    for a_index, b_index, _ in structure["bonds"]:
        pair = {structure["atoms"][a_index]["el"], structure["atoms"][b_index]["el"]}
        assert pair == {"Na", "Cl"}
    assert len(structure["bonds"]) == 54


def test_supercell_repeats_only_for_tiny_cells() -> None:
    graphite = np.array([[2.46, 0, 0], [-1.23, 2.13, 0], [0, 0, 7.8]])
    assert supercell_repeats(graphite, 4) == (3, 3, 1)
    assert supercell_repeats(np.eye(3) * 2.87, 2) == (2, 2, 2)  # bcc iron
    assert supercell_repeats(np.eye(3) * 5.64, 8) == (1, 1, 1)  # rock salt: big enough
    assert supercell_repeats(np.eye(3) * 1.0, 7) == (2, 2, 2)  # 3×3×3 would exceed 64 sites


def test_iron_fragment_is_a_block_of_cells_with_one_cell_frame() -> None:
    a = 2.87
    structure = crystal_fragment([[a, 0, 0], [0, a, 0], [0, 0, a]], [[0, 0, 0], [a / 2, a / 2, a / 2]], ["Fe", "Fe"])
    assert structure is not None
    # 2×2×2 cells: 3³ corner atoms + 2³ body centres.
    assert len(structure["atoms"]) == 27 + 8
    assert structure["cell"] == [[a, 0, 0], [0, a, 0], [0, 0, a]]
    assert composition(structure) == {"Fe": 2.0}


def test_crystal_fragment_rejects_unknown_species() -> None:
    assert crystal_fragment([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [[0, 0, 0]], ["Xx"]) is None


@pytest.mark.skipif(importlib.util.find_spec("rdkit") is None, reason="RDKit is not installed")
def test_molecule_from_smiles_ethanol() -> None:
    structure = molecule_from_smiles("CCO")
    assert structure is not None
    assert structure["kind"] == "molecule"
    assert composition(structure) == {"C": 2.0, "O": 1.0, "H": 6.0}


@pytest.mark.skipif(importlib.util.find_spec("rdkit") is None, reason="RDKit is not installed")
def test_molecule_from_smiles_places_salt_parts_side_by_side() -> None:
    structure = molecule_from_smiles("CC(=O)[O-].[Na+]")  # sodium acetate
    assert structure is not None
    assert structure["kind"] == "molecule"
    assert composition(structure) == {"C": 2.0, "O": 2.0, "H": 3.0, "Na": 1.0}


@pytest.mark.skipif(importlib.util.find_spec("rdkit") is None, reason="RDKit is not installed")
def test_molecule_from_smiles_rejects_too_many_parts() -> None:
    assert molecule_from_smiles(".".join(["O"] * 17)) is None


def _point(symbol: str, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> dict[str, float | str]:
    return {"el": symbol, "x": x, "y": y, "z": z}


def _distances(structure: dict, first: int) -> np.ndarray:
    points = np.array([[atom["x"], atom["y"], atom["z"]] for atom in structure["atoms"]])
    return np.linalg.norm(points[:first, None, :] - points[None, first:, :], axis=2)


def test_assemble_fragments_puts_counter_ion_next_to_opposite_charge() -> None:
    # Hydroxide-like anion O⁻–H (charge on O) and a Na⁺ ion.
    anion = Fragment({"kind": "molecule", "atoms": [_point("O"), _point("H", 0.96)], "bonds": [[0, 1, 1]]}, [-1, 0])
    cation = Fragment({"kind": "molecule", "atoms": [_point("Na")], "bonds": []}, [1])
    structure = assemble_fragments([cation, anion])
    assert [atom["el"] for atom in structure["atoms"]] == ["O", "H", "Na"]  # largest part first
    assert structure["bonds"] == [[0, 1, 1]]
    distances = _distances(structure, 2)
    assert distances[0, 0] == pytest.approx(ION_GAP, abs=0.01)  # Na⁺ touches O⁻
    assert distances[1, 0] > 1.5  # and keeps clear of H


def test_assemble_fragments_spreads_parts_without_overlap() -> None:
    sulfate = Fragment(
        {
            "kind": "molecule",
            "atoms": [_point("S"), _point("O", 1.5), _point("O", -1.5), _point("O", 0, 1.5), _point("O", 0, -1.5)],
            "bonds": [[0, 1, 2], [0, 2, 2], [0, 3, 1], [0, 4, 1]],
        },
        [0, 0, 0, -1, -1],
    )
    sodium = Fragment({"kind": "molecule", "atoms": [_point("Na")], "bonds": []}, [1])
    water = Fragment(
        {"kind": "molecule", "atoms": [_point("O"), _point("H", 0.96), _point("H", -0.24, 0.93)], "bonds": []},
        [0, 0, 0],
    )
    structure = assemble_fragments([sulfate, sodium, sodium, water, water])
    assert len(structure["atoms"]) == 5 + 2 + 6
    points = np.array([[atom["x"], atom["y"], atom["z"]] for atom in structure["atoms"]])
    assert np.allclose(points.mean(axis=0), 0, atol=0.01)
    # Output order: largest part first (sulfate, two waters), then the ions.
    assert [atom["el"] for atom in structure["atoms"]][-2:] == ["Na", "Na"]
    parts = [range(0, 5), range(5, 8), range(8, 11), range(11, 12), range(12, 13)]
    for i, first in enumerate(parts):
        for second in parts[i + 1 :]:
            gap = min(np.linalg.norm(points[a] - points[b]) for a in first for b in second)
            assert gap > 1.4, (first, second, gap)
    # Each Na⁺ takes its own O⁻.
    sodium_neighbours = {int(np.argmin(np.linalg.norm(points[:5] - points[index], axis=1))) for index in (11, 12)}
    assert sodium_neighbours == {3, 4}


def test_molecular_units_find_molecules_across_the_cell_boundary() -> None:
    lattice = np.eye(3) * 10.0
    # A water molecule split by the cell face (O–H 0.96 Å) and an N₂ molecule inside.
    frac = np.array([[0.98, 0.5, 0.5], [0.076, 0.5, 0.5], [0.98, 0.596, 0.5], [0.5, 0.2, 0.2], [0.61, 0.2, 0.2]])
    assert molecular_units(lattice, frac, [8, 1, 1, 7, 7]) == [{"O": 1, "H": 2}, {"N": 2}]


def test_molecular_units_detect_extended_networks() -> None:
    a = 2.87  # bcc iron: every atom bonds to its own periodic images
    assert molecular_units(np.eye(3) * a, np.array([[0, 0, 0], [0.5, 0.5, 0.5]]), [26, 26]) is None
    a = 5.64  # rock salt
    na = [[0, 0, 0], [0, 0.5, 0.5], [0.5, 0, 0.5], [0.5, 0.5, 0]]
    cl = [[0.5, 0, 0], [0, 0.5, 0], [0, 0, 0.5], [0.5, 0.5, 0.5]]
    assert molecular_units(np.eye(3) * a, np.array(na + cl, float), [11] * 4 + [17] * 4) is None


@pytest.mark.skipif(importlib.util.find_spec("spglib") is None, reason="spglib is not installed")
def test_crystal_fragment_recovers_cubic_iron_from_a_noisy_cell() -> None:
    a = 2.83
    lattice = [[a, 0, 0], [0, a * 1.004, 0], [0, 0, a * 0.997]]  # small distortion
    structure = crystal_fragment(lattice, [[0, 0, 0], [a / 2, a / 2, a / 2]], ["Fe", "Fe"])
    assert structure is not None
    cell = np.array(structure["cell"])
    lengths = np.linalg.norm(cell, axis=1)
    assert np.allclose(lengths, lengths[0], atol=1e-3)  # idealized to cubic
    assert len(structure["atoms"]) == 9  # body centre + 8 corners
