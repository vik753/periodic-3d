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
