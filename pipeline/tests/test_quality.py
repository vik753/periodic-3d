from p3d_pipeline.build import Compound, QualityReport, reconcile_formulas
from p3d_pipeline.formula import parse_formula
from p3d_pipeline.quality import (
    Verdict,
    check_formula,
    formula_from_smiles,
    has_isotopes,
    molar_mass,
    plain_formula,
    typo_variants,
)

MASSES = {"H": 1.008, "C": 12.011, "N": 14.007, "O": 15.999, "Na": 22.99, "Cl": 35.45, "K": 39.098, "B": 10.81}
ELECTRONEGATIVITY = {"K": 0.82, "Na": 0.93, "Cl": 3.16, "O": 3.44, "B": 2.04, "H": 2.2, "C": 2.55}


def _compound(qid: str, formula: str, **kwargs: object) -> Compound:
    counts = parse_formula(formula)
    assert counts
    compound = Compound(
        id=qid,
        formula=formula,
        counts=counts,
        names={"en": qid},
        articles={"en": qid},
        fame=1,
        cid=kwargs.pop("cid", None),  # type: ignore[arg-type]
        classes=[],
        mp_hint=None,
    )
    for key, value in kwargs.items():
        setattr(compound, key, value)
    return compound


def test_isotopes_and_typos() -> None:
    assert has_isotopes("D₂O") and has_isotopes("C²HCl₃") and not has_isotopes("TiO₂")
    assert typo_variants("KCIO₃") == [{"K": 1.0, "Cl": 1.0, "O": 3.0}]


def test_smiles_formula() -> None:
    assert formula_from_smiles("[K+].[O-]Cl(=O)=O") == {"K": 1.0, "Cl": 1.0, "O": 3.0}
    assert formula_from_smiles("not a smiles") is None
    assert formula_from_smiles(None) is None


def test_check_formula_verdicts() -> None:
    water = parse_formula("H2O")
    assert water
    assert check_formula("H₂O", water, "H2O", None).verdict == Verdict.OK
    assert check_formula("H₂O", water, None, None).verdict == Verdict.NO_PUBCHEM
    # A typo in Wikidata: carbon and iodine instead of chlorine.
    chlorate = parse_formula("KCIO3")
    assert chlorate
    assert check_formula("KCIO₃", chlorate, "ClKO3", None).verdict == Verdict.WIKIDATA_FIXED
    # A nerve agent without its phosphorus: the SMILES agrees with PubChem.
    soman = parse_formula("C7H16FO2")
    assert soman
    smiles = "CC(C(C)(C)C)OP(C)(=O)F"
    assert check_formula("C₇H₁₆FO₂", soman, "C7H16FO2P", smiles).verdict == Verdict.WIKIDATA_FIXED
    # PubChem points to the anhydrous salt: a hydrate difference, the Wikidata formula stays.
    borax = parse_formula("Na2B4O7·10H2O")
    assert borax
    assert check_formula("Na₂B₄O₇·10H₂O", borax, "B4Na2O7", None).verdict == Verdict.HYDRATE
    # PubChem keeps the hydrate: not an error, the Wikidata formula stays.
    ascorbate = parse_formula("C12H14CaO12")
    assert ascorbate
    assert check_formula("CaC₁₂H₁₄O₁₂", ascorbate, "C12H18CaO14", None).verdict == Verdict.HYDRATE
    # A dye without its chloride in PubChem: the SMILES (copied from PubChem) is no proof.
    rhodamine = parse_formula("C28H31ClN2O3")
    assert rhodamine
    cation_smiles = "CCNc1cc2[o+]c3cc(NCC)c(C)cc3c(-c3ccccc3C(=O)OCC)c2cc1C"
    assert check_formula("C₂₈H₃₁ClN2O₃", rhodamine, "C28H31N2O3", cation_smiles).verdict == Verdict.DISAGREE
    # A dimer record: same proportions.
    dimer = parse_formula("C10H10Cl2V")
    assert dimer
    assert check_formula("C₁₀H₁₀Cl₂V", dimer, "C20H20Cl4V2", None).verdict == Verdict.SCALED


def test_molar_mass_and_plain_formula() -> None:
    water = parse_formula("H2O")
    assert water
    assert molar_mass(water, MASSES) == 18.015
    assert molar_mass({"Xx": 1.0}, MASSES) is None
    assert plain_formula({"O": 3.0, "K": 1.0, "Cl": 1.0}) == "ClKO3"


def test_reconcile_fixes_wikidata_drops_pubchem_and_sets_mass() -> None:
    chlorate = _compound("Q1", "KCIO₃", cid=6426, pubchem={"formula": "ClKO3", "mass": 122.55, "iupac": "x"})
    water = _compound("Q283", "H₂O", cid=962, pubchem={"formula": "H2O", "mass": 18.015})
    borax = _compound("Q5", "Na₂B₄O₇·10H₂O", cid=10219853, pubchem={"formula": "B4Na2O7", "mass": 201.2})
    dye = _compound("Q6", "C₂₈H₃₁ClN₂O₃", cid=13806, pubchem={"formula": "C28H31N2O3", "mass": 443.6})
    salt = _compound("Q2314", "NaCl")
    report: QualityReport = reconcile_formulas([chlorate, water, borax, dye, salt], MASSES, ELECTRONEGATIVITY)

    assert chlorate.counts == {"K": 1.0, "Cl": 1.0, "O": 3.0}
    assert chlorate.formula == "KClO₃"
    assert chlorate.quality == {"wikidataFormula": "KCIO₃"}
    assert (chlorate.mass, chlorate.mass_source) == (122.55, "pubchem")

    assert (water.mass, water.mass_source) == (18.015, "pubchem")
    assert water.quality == {}

    # Borax: PubChem has the anhydrous salt; the decahydrate formula and its mass stay.
    assert borax.quality == {}
    assert (borax.mass, borax.mass_source) == (381.363, "formula")

    # A dye that PubChem lists without its chloride: both formulas shown, no PubChem details.
    assert dye.quality == {"pubchemFormula": "C28H31N2O3"}
    assert dye.mass is None
    assert dye.pubchem == {"formula": "C28H31N2O3"}

    # No PubChem record: the mass comes from the formula.
    assert salt.mass_source == "formula"
    assert salt.mass == 58.44

    assert report.verdicts[Verdict.WIKIDATA_FIXED] == 1
    assert report.verdicts[Verdict.DISAGREE] == 1
    assert report.verdicts[Verdict.HYDRATE] == 1
    assert report.examples[Verdict.WIKIDATA_FIXED][0].startswith("Q1 KClO₃")


def test_cell_shapes() -> None:
    from p3d_pipeline.golden import cell_shape

    assert cell_shape([[5.6, 0, 0], [0, 5.6, 0], [0, 0, 5.6]]) == "cubic"
    assert cell_shape([[2.46, 0, 0], [-1.23, 2.1304, 0], [0, 0, 6.7]]) == "hexagonal"
    assert cell_shape([[3, 0, 0], [0, 4, 0], [0, 0, 5]]) == "other"


def test_golden_check_reports_each_problem() -> None:
    from p3d_pipeline.golden import Golden, check

    water = Golden("Q283", "Water", "H2O", 18.015, "molecule")
    card = {"names": {"en": "water"}, "hill": "H2O", "mass": 18.015, "structure": {"kind": "molecule"}}
    assert check(water, card, None) == []
    wrong = {"names": {"en": "Water"}, "hill": "HO", "mass": 20.0, "structure": {"kind": "flat"}}
    assert len(check(water, wrong, None)) == 3
    assert check(water, None, None) == ["Q283 Water: missing from the dataset"]
    salt = Golden("Q2314", "Sodium chloride", "ClNa", 58.44, "crystal", "cubic")
    salt_card = {"names": {"en": "sodium chloride"}, "hill": "ClNa", "mass": 58.44, "structure": {"kind": "crystal"}}
    assert check(salt, salt_card, {"cell": [[5.6, 0, 0], [0, 5.6, 0], [0, 0, 5.6]]}) == []
    assert check(salt, salt_card, {"cell": [[5.6, 0, 0], [0, 5.6, 0], [0, 0, 7]]}) == [
        "Q2314 Sodium chloride: unit cell is other instead of cubic"
    ]


def test_plausible_fix_rules() -> None:
    from p3d_pipeline.quality import plausible_fix, water_difference

    def counts(text: str) -> dict[str, float]:
        value = parse_formula(text)
        assert value
        return value

    assert plausible_fix(counts("C5H10O2"), counts("C5H12O2"))  # 1,5-pentanediol: two H missing
    assert plausible_fix(counts("C7H16FO2"), counts("C7H16FO2P"))  # soman: phosphorus missing
    assert not plausible_fix(counts("C6H13BO2"), counts("C6H12BO2"))  # one H: a charge or radical form
    assert not plausible_fix(counts("C8H12Mo2O8"), counts("C8H16Mo2O8"))  # a metal complex
    assert not plausible_fix(counts("UC"), counts("CH4U"))  # inorganic
    assert not plausible_fix(counts("C28H31ClN2O3"), counts("C28H31N2O3"))  # chloride would vanish
    assert water_difference(counts("C12H18CaO14"), counts("C12H14CaO12")) == 2
    assert water_difference(counts("C12H18CaO14"), counts("C12H14CaO13")) is None
