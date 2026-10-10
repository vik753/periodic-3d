from p3d_pipeline.embeddings import compound_vector, element_vectors, nearest, ppmi
from p3d_pipeline.formula import parse_formula


def _corpus() -> list[dict[str, float]]:
    formulas = []
    for metal in ("Li", "Na", "K", "Rb"):
        for anion in ("Cl", "Br", "I", "F"):
            formulas.append(f"{metal}{anion}")
        formulas += [f"{metal}2O", f"{metal}OH", f"{metal}2S"]
    for metal in ("Mg", "Ca", "Sr", "Ba"):
        formulas += [f"{metal}O", f"{metal}Cl2", f"{metal}CO3", f"{metal}S"]
    formulas += ["CH4", "C2H6", "C2H5OH", "CO2", "H2O", "CH3OH", "C6H6", "NH3"]
    return [counts for formula in formulas if (counts := parse_formula(formula))]


def test_ppmi_is_non_negative() -> None:
    import numpy as np

    matrix = ppmi(np.array([[0.0, 3.0], [3.0, 0.0]]))
    assert (matrix >= 0).all()


def test_alkali_metals_are_neighbours() -> None:
    vectors = element_vectors(_corpus(), dim=8)
    neighbours = [symbol for symbol, _ in nearest(vectors, "Na", 3)]
    assert set(neighbours) <= {"Li", "K", "Rb", "Cl", "Br", "I", "F"}
    assert any(symbol in neighbours for symbol in ("Li", "K", "Rb"))


def test_compound_vector_is_a_unit_vector() -> None:
    vectors = element_vectors(_corpus(), dim=8)
    vector = compound_vector({"Na": 1, "Cl": 1}, vectors)
    assert vector is not None
    assert abs(sum(x * x for x in vector) - 1) < 1e-3
    assert compound_vector({"Xe": 1}, vectors) is None
