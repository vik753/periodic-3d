import importlib.util

import numpy as np
import pytest

from p3d_pipeline.formula import same_proportions
from p3d_pipeline.structures import (
    composition,
    crystal_fragment,
    molecular_units,
    molecule_from_smiles,
    parse_sdf,
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


def test_crystal_fragment_rejects_unknown_species() -> None:
    assert crystal_fragment([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [[0, 0, 0]], ["Xx"]) is None


@pytest.mark.skipif(importlib.util.find_spec("rdkit") is None, reason="RDKit is not installed")
def test_molecule_from_smiles_ethanol() -> None:
    structure = molecule_from_smiles("CCO")
    assert structure is not None
    assert structure["kind"] == "molecule"
    assert composition(structure) == {"C": 2.0, "O": 1.0, "H": 6.0}


@pytest.mark.skipif(importlib.util.find_spec("rdkit") is None, reason="RDKit is not installed")
def test_molecule_from_smiles_rejects_salts() -> None:
    assert molecule_from_smiles("[Na+].[Cl-]") is None


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
