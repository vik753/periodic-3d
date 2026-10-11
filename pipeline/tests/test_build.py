from pathlib import Path

from p3d_pipeline.build import (
    Compound,
    Options,
    build_elements,
    build_pairs,
    capitalize,
    prefers_crystal,
    select_compounds,
)
from p3d_pipeline.sources.wikidata import CompoundRecord, ElementLabels


def _options(**kwargs: object) -> Options:
    return Options(out_dir=Path("out"), cache_dir=Path("cache"), version="test", **kwargs)  # type: ignore[arg-type]


def _record(qid: str, formula: str, sitelinks: int, **kwargs: object) -> CompoundRecord:
    record = CompoundRecord(qid=qid, formulas={formula}, articles={"en": qid}, sitelinks=sitelinks)
    for key, value in kwargs.items():
        setattr(record, key, value)
    return record


def test_select_compounds_orders_by_fame_and_filters_elements() -> None:
    records = {
        "Q1": _record("Q1", "H₂O", 300, labels={"ru": "вода"}),
        "Q2": _record("Q2", "Fe₂O₃", 80),
        "Q3": _record("Q3", "NaCl", 200),
        "Q4": _record("Q4", "(C₂H₄)ₙ", 150),
    }
    selected = select_compounds(records, _options(only_elements=frozenset({"H", "O", "Fe"})))
    assert [compound.id for compound in selected] == ["Q1", "Q2"]
    assert selected[0].names["ru"] == "Вода"
    assert selected[1].elements == ["O", "Fe"]


def test_select_compounds_limit() -> None:
    records = {f"Q{i}": _record(f"Q{i}", "H₂O", i) for i in range(1, 6)}
    assert [c.id for c in select_compounds(records, _options(limit=2))] == ["Q5", "Q4"]


def _compound(formula_counts: dict[str, float], smiles: str = "", qid: str = "Q9") -> Compound:
    compound = Compound(
        id=qid,
        formula="",
        counts=formula_counts,
        names={},
        articles={},
        fame=1,
        cid=None,
        classes=[],
        mp_hint=None,
    )
    compound.pubchem = {"smiles": smiles}
    return compound


def test_prefers_crystal() -> None:
    assert prefers_crystal(_compound({"Fe": 2, "O": 3}), has_3d=False)
    assert prefers_crystal(_compound({"Fe": 1}), has_3d=False)
    assert not prefers_crystal(_compound({"O": 2}), has_3d=True)
    assert not prefers_crystal(_compound({"H": 2, "O": 1}), has_3d=True)
    assert prefers_crystal(_compound({"Si": 1, "O": 2}), has_3d=True)  # quartz, not O=Si=O
    assert prefers_crystal(_compound({"Ca": 1, "C": 1, "O": 3}, "C(=O)([O-])[O-].[Ca+2]"), has_3d=False)
    assert not prefers_crystal(_compound({"C": 2, "H": 6, "O": 1}, "CCO"), has_3d=True)
    assert prefers_crystal(_compound({"C": 1}, qid="Q5283"), has_3d=False)  # diamond
    assert not prefers_crystal(_compound({"C": 1}, qid="Q999"), has_3d=False)  # unknown carbon form


def test_build_pairs_counts_and_order() -> None:
    compounds = [_compound({"Fe": 2, "O": 3}, qid="QA"), _compound({"H": 2, "O": 1}, qid="QB")]
    compounds.append(_compound({"Fe": 1, "O": 1, "H": 1}, qid="QC"))
    pairs = {(pair["a"], pair["b"]): pair for pair in build_pairs(compounds)}
    assert pairs[(8, 26)]["count"] == 2
    assert pairs[(8, 26)]["top"] == ["QA", "QC"]
    assert pairs[(1, 8)]["count"] == 2


def test_build_elements_uses_ukrainian_nomenclature() -> None:
    table = {26: {"Name": "Iron", "AtomicMass": "55.845", "CPKHexColor": "E06633"}}
    labels = {26: ElementLabels(qid="Q677", z=26, labels={"ru": "железо", "uk": "залізо", "la": "ferrum"})}
    elements = build_elements(table, labels)
    iron = elements[25]
    assert iron["names"] == {"en": "Iron", "ru": "Железо", "uk": "Ферум", "la": "Ferrum"}
    assert iron["substanceNames"]["uk"] == "залізо"
    assert iron["mass"] == 55.845
    assert iron["cpk"] == "#E06633"
    assert len(elements) == 118


def test_capitalize_keeps_locants() -> None:
    assert capitalize("хлорид натрия") == "Хлорид натрия"
    assert capitalize("n-butane") == "n-butane"
    assert capitalize("1,2-dichloroethane") == "1,2-dichloroethane"


def test_select_compounds_skips_elements_atoms_and_ions_of_one_atom() -> None:
    records = {
        "Q677": _record("Q677", "Fe", 250),  # the element item itself
        "Q54389": _record("Q54389", "³H", 79),  # tritium: a single atom
        "Q506710": _record("Q506710", "H⁺", 31),  # hydron
        "Q5283": _record("Q5283", "C", 120),  # diamond: an allotrope, kept
        "Q181395": _record("Q181395", "Fe²⁺Fe³⁺₂O₄", 68, classes={"Q12089225"}),  # magnetite
        "Q849881": _record("Q849881", "H₃O⁺", 45),  # hydronium: an ion, kept
        "Q104116": _record("Q104116", "OH", 63, classes={"Q141501897"}),  # hydroxyl group: not a substance
    }
    selected = select_compounds(
        records, _options(), excluded=frozenset({"Q677"}), electronegativity={"Fe": 1.83, "O": 3.44}
    )
    by_id = {compound.id: compound for compound in selected}
    assert set(by_id) == {"Q5283", "Q181395", "Q849881"}
    assert by_id["Q181395"].formula == "Fe₃O₄"
    assert by_id["Q181395"].mineral
    assert by_id["Q849881"].charged


def test_structure_methods() -> None:
    from p3d_pipeline.build import structure_methods

    ion = _compound({"N": 1, "H": 4})
    ion.charged = True
    assert structure_methods(ion, wants_crystal=False) == ["pubchem3d", "rdkit"]
    assert structure_methods(_compound({"H": 2, "O": 1}), wants_crystal=False)[-1] == "crystal"
    assert structure_methods(_compound({"Fe": 2, "O": 3}), wants_crystal=True)[0] == "crystal"


def test_molecular_crystal_matches() -> None:
    from p3d_pipeline.build import molecular_crystal_matches

    ice = {"kind": "crystal", "units": [{"H": 2, "O": 1}, {"H": 2, "O": 1}]}
    peroxide = {"kind": "crystal", "units": [{"H": 2, "O": 2}]}
    network = {"kind": "crystal", "units": None}
    assert molecular_crystal_matches(ice, {"H": 2, "O": 1})
    assert not molecular_crystal_matches(peroxide, {"H": 1, "O": 1})
    assert not molecular_crystal_matches(network, {"H": 2, "O": 1})


def test_best_candidate_prefers_long_standing_entries() -> None:
    from p3d_pipeline.sources.optimade import Candidate, best_candidate

    options = [
        Candidate("mp-2516584", "C", 8, 0.0),
        Candidate("mp-48", "C", 4, 0.008),
        Candidate("mp-66", "C", 2, 0.13),
    ]
    best = best_candidate(options)
    assert best is not None and best.id == "mp-48"  # within the window, the oldest id wins
    assert best_candidate([]) is None


def test_select_compounds_skips_giant_formulas_and_finds_smiles() -> None:
    records = {
        "Q43041": _record("Q43041", "C2952H4664Fe4321O8125S8", 100),  # hemoglobin with a broken formula
        "Q37525": _record("Q37525", "C6H12O6", 114),  # glucose: a group of isomers, no SMILES of its own
        "Q153": _record("Q153", "C2H6O", 132, smiles={"CCO"}, canonical_smiles={"OCC"}),
        "Q2270": _record("Q2270", "C6H6", 93, canonical_smiles={"c1ccccc1"}),
    }
    by_id = {compound.id: compound for compound in select_compounds(records, _options())}
    assert set(by_id) == {"Q37525", "Q153", "Q2270"}
    assert by_id["Q153"].smiles == "CCO"  # isomeric SMILES first
    assert by_id["Q2270"].smiles == "c1ccccc1"
    assert by_id["Q37525"].smiles and by_id["Q37525"].smiles.count("O") == 6
    by_id["Q153"].pubchem = {"smiles": "C(C)O"}
    assert by_id["Q153"].smiles == "C(C)O"  # PubChem wins
