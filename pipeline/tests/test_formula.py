import pytest

from p3d_pipeline.formula import (
    hill_formula,
    parse_formula,
    reduced_formula,
    same_proportions,
    to_subscripts,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("H₂O", {"H": 2, "O": 1}),
        ("Fe₂O₃", {"Fe": 2, "O": 3}),
        ("CuSO₄·5H₂O", {"Cu": 1, "S": 1, "O": 9, "H": 10}),
        ("[Fe(CN)₆]³⁻", {"Fe": 1, "C": 6, "N": 6}),
        ("K₄[Fe(CN)₆]", {"K": 4, "Fe": 1, "C": 6, "N": 6}),
        ("Ca(OH)₂", {"Ca": 1, "O": 2, "H": 2}),
        ("D₂O", {"H": 2, "O": 1}),
        ("NH₄⁺", {"N": 1, "H": 4}),
        ("Na₂CO₃ · 10H₂O", {"Na": 2, "C": 1, "O": 13, "H": 20}),
    ],
)
def test_parse_formula(raw: str, expected: dict[str, float]) -> None:
    assert parse_formula(raw) == expected


@pytest.mark.parametrize("raw", ["(C₂H₄)ₙ", "Fe₁₋ₓO", "Xx2", "", "R-OH"])
def test_parse_formula_rejects_variable_or_unknown(raw: str) -> None:
    assert parse_formula(raw) is None


def test_hill_formula() -> None:
    assert hill_formula({"O": 1, "H": 2}) == "H2O"
    assert hill_formula({"C": 2, "H": 6, "O": 1}) == "C2H6O"
    assert hill_formula({"Na": 1, "Cl": 1}) == "ClNa"


def test_reduced_formula() -> None:
    assert reduced_formula({"Na": 1, "Cl": 1}) == "ClNa"
    assert reduced_formula({"C": 6, "H": 12, "O": 6}) == "CH2O"
    assert reduced_formula({"Fe": 2, "O": 3}) == "Fe2O3"
    assert reduced_formula({"Fe": 0.95, "O": 1}) is None


def test_to_subscripts() -> None:
    assert to_subscripts("Fe2O3") == "Fe₂O₃"
    assert to_subscripts("Ca(OH)2") == "Ca(OH)₂"


def test_same_proportions() -> None:
    assert same_proportions({"Na": 4, "Cl": 4}, {"Na": 1, "Cl": 1})
    assert not same_proportions({"Fe": 2, "O": 3}, {"Fe": 3, "O": 4})
