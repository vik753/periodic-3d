"""Uses of substances (task U.2): vocabulary, matcher, ChEBI roles, card and USGS data."""

from __future__ import annotations

import json

from p3d_pipeline.uses import registry
from p3d_pipeline.uses.collect import USGS_FILE, ChebiOntology, Collector, Evidence, Uses, card
from p3d_pipeline.uses.match import Context, Matcher
from p3d_pipeline.uses.vocabulary import SPHERE_IDS, TERM_BY_ID, TERMS, atc_term

MATCHER = Matcher()


def terms(heading: str, source: str, strings: list[str]) -> set[str]:
    rule = registry.PUBCHEM_RULES[(heading, source)]
    return {hit.term for hit in MATCHER.find(strings, rule.context)}


def test_vocabulary_is_complete() -> None:
    assert len(SPHERE_IDS) == 10
    assert {term.sphere for term in TERMS} == set(SPHERE_IDS)
    for term in TERMS:
        assert all(term.names[language] for language in ("uk", "ru", "en")), term.id
    for heading_source, rule in registry.PUBCHEM_RULES.items():
        assert rule.source in registry.SOURCES, heading_source
        assert rule.context.default is None or rule.context.default in TERM_BY_ID


def test_atc_codes_map_to_medicine_terms() -> None:
    assert atc_term("N02BA01") == "analgesia"  # aspirin
    assert atc_term("N06BC01") == "nervous_system"  # caffeine
    assert atc_term("D08AG02") == "antiseptic"  # povidone-iodine
    assert atc_term("V03AB03") == "antidote"
    assert atc_term("V07AB") is None  # solvents for injections: not a therapeutic use
    assert atc_term("L01XA01") == "oncology"


def test_hsdb_uses_and_negations() -> None:
    assert terms("Uses", registry.HSDB, ["High explosive, production of dynamite", "Rocket propellants"]) >= {
        "explosives",
        "rocket_fuel",
    }
    # A pesticide that is not registered any more, and a former medical use.
    assert (
        terms(
            "Uses",
            registry.HSDB,
            ["For benzene (USEPA/OPP Pesticide Code: 008801) there are 0 labels match. /SRP: Not registered/"],
        )
        == set()
    )
    assert (
        terms("Therapeutic Uses", registry.HSDB, ["MEDICATION (VET): Has been used as a disinfectant. /Former Use/"])
        == set()
    )


def test_production_of_a_product_is_not_the_product() -> None:
    found = terms("Uses", registry.HSDB, ["Used in the production of dyes, insecticides and pharmaceuticals"])
    assert "insecticide" not in found and "drug" not in found
    assert "pharma_manufacturing" in found


def test_exposure_categories_and_past_uses_are_skipped() -> None:
    found = terms(
        "Uses",
        registry.HAZMAP,
        [
            "Benzene was used in the past as a solvent in inks. "
            "Today, it is used mainly to synthesize organic chemicals.",
            "Smoking cigarettes [Category: Food & Drugs]",
        ],
    )
    assert found == {"chemical_feedstock"}


def test_category_sources_use_their_context() -> None:
    assert terms(
        "Use Classification",
        registry.JECFA,
        ["Food Additives -> ANTIOXIDANT; NUTRIENT_SUPPLEMENT -> JECFA Functional Classes"],
    ) >= {"food_antioxidant", "fortification"}
    assert terms("Cosmetics", registry.NORMAN, ["Preservative"]) == {"cosmetics"}
    assert terms("Cosmetics", registry.NORMAN, ["Hair dyeing"]) == {"hair_dye"}
    assert terms("Drug Classes", "LiverTox", ["Substance Abuse Treatment Agents"]) == {"nervous_system"}
    assert (
        terms(
            "Use Classification", registry.NORMAN, ["Environmental transformation -> Pesticide transformation products"]
        )
        == set()
    )


def test_priority_resolves_overlaps() -> None:
    context = Context()
    assert MATCHER.sentence_terms("used in fuel cells", context) == ["fuel_cells"]
    assert "pigments_dyes" not in MATCHER.sentence_terms("approved as a food colour", context)
    assert MATCHER.sentence_terms("PET imaging of tumours", context) == ["nuclear_medicine"]
    assert "solvent" not in MATCHER.sentence_terms("gold leaf is thinner than paper", context)


def test_chebi_application_roles() -> None:
    obo = b"""[Term]
id: CHEBI:33232
name: application

[Term]
id: CHEBI:52217
name: pharmaceutical
is_a: CHEBI:33232

[Term]
id: CHEBI:35480
name: analgesic
is_a: CHEBI:52217

[Term]
id: CHEBI:24527
name: herbicide
is_a: CHEBI:33232

[Term]
id: CHEBI:1
name: example substance
relationship: RO:0000087 CHEBI:24527
relationship: RO:0000087 CHEBI:35480
"""
    ontology = ChebiOntology.parse(obo)
    assert ontology.application_roles("CHEBI:1") == ["CHEBI:24527"]  # the pharmaceutical branch is skipped
    assert ontology.lineage("CHEBI:35480") == ["CHEBI:35480", "CHEBI:52217"]


def test_card_drops_umbrella_terms_and_orders_spheres() -> None:
    uses = Uses(
        evidence=[
            Evidence("pesticide", "eu_pesticides", "u1"),
            Evidence("herbicide", "eu_pesticides", "u1"),
            Evidence("herbicide", "hsdb", "u2", "Used as a selective herbicide for the control of broadleaf weeds."),
            Evidence("solvent", "chebi", "u3"),
        ],
        notes={"eu_not_approved"},
    )
    result = card(uses)
    assert result is not None
    assert [sphere["id"] for sphere in result["spheres"]] == ["agriculture", "industry"]
    herbicide = result["spheres"][0]["terms"][0]
    assert herbicide["id"] == "herbicide" and herbicide["sources"] == ["eu_pesticides", "hsdb"]
    assert herbicide["notes"] == ["eu_not_approved"]
    assert all(term["id"] != "pesticide" for sphere in result["spheres"] for term in sphere["terms"])
    assert result["quotes"][0]["source"] == "hsdb"
    assert {source["id"] for source in result["sources"]} == {"eu_pesticides", "hsdb", "chebi"}
    assert card(Uses()) is None


def test_usgs_curated_data() -> None:
    data = json.loads(USGS_FILE.read_text(encoding="utf-8"))
    symbols = {symbol for entry in data["commodities"] for symbol in entry["elements"]}
    assert {"Li", "Cu", "He", "Fe", "Ag", "Na", "Nd"} <= symbols
    for entry in data["commodities"]:
        assert entry["url"].startswith("https://pubs.usgs.gov/")
        assert entry["quote"]
        total = sum(item.get("share", 0) for item in entry["shares"])
        assert total <= 101, entry["commodity"]["en"]
        for item in entry["shares"]:
            assert all(item["names"][language] for language in ("uk", "ru", "en"))
            assert item.get("term") is None or item["term"] in TERM_BY_ID
        assert all(term in TERM_BY_ID for term in entry["terms"])
    lithium = next(entry for entry in data["commodities"] if entry["elements"] == ["Li"])
    assert lithium["shares"][0] == {
        "names": {"uk": "акумулятори", "ru": "аккумуляторы", "en": "batteries"},
        "share": 88,
        "term": "batteries",
    }


def test_therapeutic_uses_read_labels_not_studies() -> None:
    found = terms(
        "Therapeutic Uses",
        registry.HSDB,
        [
            "Vasodilator Agents",
            "In a randomized trial of 40 patients, the drug reduced the frequency of migraine attacks. It was safe.",
        ],
    )
    assert found == {"cardiovascular"}


def test_inert_ingredients_are_not_the_product() -> None:
    assert "pesticide" not in terms("Uses", registry.HSDB, ["Used as an inert ingredient in pesticide formulations"])


def test_isotope_notes_give_one_term_per_section() -> None:
    context = registry.ELEMENT_RULES["Isotopes in Medicine"]
    hits = MATCHER.find(["Iodine-131 is used to treat thyroid cancer and hyperthyroidism."], context)
    assert {hit.term for hit in hits} == {"nuclear_medicine"}


def test_category_patterns_stay_in_their_domain() -> None:
    # "Stabilizer" from EPA CDR is not a food additive; JECFA colour retention is not a colour.
    assert "emulsifier" not in terms("Industry Uses", registry.CDR, ["Stabilizer", "Solvent"])
    assert terms(
        "Food Additive Classes", registry.JECFA, ["Food Additives -> PRESERVATIVE; COLOUR_RETENTION_AGENT"]
    ) == {
        "food_additive",
        "food_preservative",
    }
    # JECFA also evaluates residues and contaminants: no "food additive" by default.
    assert terms("Use Classification", registry.JECFA, ["Veterinary drug residue"]) == set()


def test_eu_only_unapproved_pesticide_is_dropped() -> None:
    uses = Uses(
        evidence=[Evidence("pesticide", "eu_pesticides", "u1"), Evidence("beverages", "hsdb", "u2")],
        notes={"eu_not_approved"},
    )
    result = card(uses)
    assert result is not None
    assert [sphere["id"] for sphere in result["spheres"]] == ["food"]
    assert [source["id"] for source in result["sources"]] == ["hsdb"]


def test_shares_order_terms_and_spheres() -> None:
    uses = Uses(
        evidence=[
            Evidence("biocide", "hsdb", "u"),
            Evidence("biocide", "lanl", "u"),
            Evidence("biocide", "jlab", "u"),
            Evidence("construction", "usgs_mcs", "u"),
            Evidence("automotive", "usgs_mcs", "u"),
        ],
        shares=[
            {
                "url": "u",
                "items": [
                    {"names": {"en": "building"}, "share": 42, "term": "construction"},
                    {"names": {"en": "transport"}, "share": 18, "term": "automotive"},
                ],
            }
        ],
    )
    result = card(uses)
    assert result is not None
    assert result["spheres"][0]["id"] == "materials"  # 42% beats three mentions
    industry = next(sphere for sphere in result["spheres"] if sphere["id"] == "industry")
    assert [term["id"] for term in industry["terms"]] == ["automotive", "biocide"]


def test_chebi_ancestor_gives_only_specific_terms() -> None:
    obo = b"""[Term]
id: CHEBI:33232
name: application

[Term]
id: CHEBI:33286
name: agrochemical
is_a: CHEBI:33232

[Term]
id: CHEBI:2
name: plant activator
is_a: CHEBI:33286

[Term]
id: CHEBI:24852
name: insecticide
is_a: CHEBI:33286

[Term]
id: CHEBI:3
name: proinsecticide
is_a: CHEBI:24852
"""
    ontology = ChebiOntology.parse(obo)
    collector = Collector(fetcher=None)  # type: ignore[arg-type]
    assert collector._chebi_terms(ontology, "CHEBI:2") == []  # not a pesticide
    assert collector._chebi_terms(ontology, "CHEBI:3") == ["insecticide"]
