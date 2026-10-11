from collections import Counter
from pathlib import Path

from p3d_pipeline import gnome

CIF = (Path(__file__).parent / "fixtures" / "gnome-517994b984.cif").read_text(encoding="utf-8")


def test_parse_cif_reads_cell_and_sites() -> None:
    cell = gnome.parse_cif(CIF)
    assert cell is not None
    assert cell.parameters[0] > 1 and cell.parameters[5] > 1
    assert len(cell.sites) > 0
    assert all(1 <= z <= 118 for z, *_ in cell.sites)


def test_parse_cif_rejects_partial_occupancy_and_broken_files() -> None:
    assert gnome.parse_cif("data_x\n_cell_length_a 1\n") is None
    partial = """data_x
_cell_length_a 3
_cell_length_b 3
_cell_length_c 3
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
 _atom_site_type_symbol
 _atom_site_label
 _atom_site_fract_x
 _atom_site_fract_y
 _atom_site_fract_z
 _atom_site_occupancy
  Fe  Fe0  0  0  0  0.5
"""
    assert gnome.parse_cif(partial) is None
    assert gnome.parse_cif(partial.replace("0.5", "1")) is not None


def test_compact_wraps_and_scales_fractions() -> None:
    sites = [(11, 0.0, 0.5, 1.0), (17, -0.25, 0.99999, 0.12345)]
    cell = gnome.Cell(parameters=[3.98766, 3.98, 3.98, 60.0, 60.0, 60.0], sites=sites)
    data = gnome.compact(cell)
    assert data["cell"][0] == 3.9877
    assert data["sites"] == [11, 0, 5000, 0, 17, 7500, 0, 1234]


def test_material_record_and_composition() -> None:
    assert gnome.parse_composition("Cs1S6Zr3") == {"Cs": 1, "S": 6, "Zr": 3}
    cell = gnome.Cell(parameters=[5, 5, 5, 90, 90, 90], sites=[(55, 0, 0, 0)] + [(40, 0.1 * i, 0, 0) for i in range(3)])
    row = {
        "MaterialId": "000006a8c4",
        "Composition": "Cs1S6Zr3",
        "Reduced Formula": "Cs(ZrS2)3",
        "Space Group": "C2/m",
        "Space Group Number": "12",
        "Crystal System": "monoclinic",
        "Formation Energy Per Atom": "-1.90581",
        "Decomposition Energy Per Atom": "-0.1625",
        "Bandgap": "",
        "Dimensionality Cheon": "intercalated ion",
    }
    record = gnome.material_record(row, cell, {"000006a8c4": -0.1})
    assert record["elements"] == ["S", "Zr", "Cs"]  # by atomic number
    assert record["spaceGroupNumber"] == 12
    assert record["formationEnergy"] == -1.9058
    assert record["bandgap"] is None
    assert record["r2scanDecompositionEnergy"] == -0.1
    assert record["nsites"] == 4


def test_cell_composition_matches_the_cif_formula() -> None:
    cell = gnome.parse_cif(CIF)
    assert cell is not None
    assert cell.composition() == Counter({"Tm": 10, "In": 2, "Sn": 1, "Sb": 3})
