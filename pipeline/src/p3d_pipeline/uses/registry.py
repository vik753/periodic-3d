"""Sources of uses (task U.2): who says it, under which license, and how we read it.

PubChem gathers use records from many databases. Each (heading, PubChem source) pair has
a reading rule: which spheres it may speak about, whether its strings are category
labels, whether a sentence needs a use cue, and the term for a record that names no
known term. Pairs not listed here are not used: monitoring lists (EPA IRIS, USGS
water-quality screening, USDA residue program) name substances that are measured, not
used.

`quote`: the text is a U.S. Government work (public domain); the card may show a short
quote from it. Other sources give only terms and a link.
"""

from __future__ import annotations

from dataclasses import dataclass

from .match import Context
from .vocabulary import SPHERE_IDS


@dataclass(frozen=True)
class Source:
    id: str
    short: str
    name: str
    license: str
    homepage: str
    quote: bool = False


PUBLIC_DOMAIN = "Public domain (U.S. Government work)"

SOURCES: dict[str, Source] = {
    source.id: source
    for source in (
        Source(
            "hsdb",
            "HSDB",
            "Hazardous Substances Data Bank (U.S. National Library of Medicine)",
            PUBLIC_DOMAIN,
            "https://pubchem.ncbi.nlm.nih.gov/source/11933",
            quote=True,
        ),
        Source(
            "hazmap",
            "Haz-Map",
            "Haz-Map: Information on Hazardous Chemicals and Occupational Diseases",
            "Facts via PubChem; text © Haz-Map",
            "https://haz-map.com",
        ),
        Source(
            "epa_cpdat",
            "EPA CPDat",
            "EPA Chemical and Products Database",
            PUBLIC_DOMAIN,
            "https://www.epa.gov/chemical-research/chemical-and-products-database-cpdat",
        ),
        Source(
            "epa_cdr",
            "EPA CDR",
            "EPA Chemical Data Reporting",
            PUBLIC_DOMAIN,
            "https://www.epa.gov/chemical-data-reporting",
        ),
        Source(
            "epa_hap",
            "EPA",
            "EPA Hazardous Air Pollutants fact sheets",
            PUBLIC_DOMAIN,
            "https://www.epa.gov/haps",
            quote=True,
        ),
        Source(
            "epa_saferchoice",
            "EPA Safer Choice",
            "EPA Safer Chemical Ingredients List",
            PUBLIC_DOMAIN,
            "https://www.epa.gov/saferchoice/safer-ingredients",
        ),
        Source(
            "epa_ecotox", "EPA", "EPA Pesticide Ecotoxicity Database", PUBLIC_DOMAIN, "https://ecotox.ipmcenters.org"
        ),
        Source("cir", "CIR", "Cosmetic Ingredient Review", "Facts via PubChem", "https://www.cir-safety.org"),
        Source(
            "cscp", "CSCP", "California Safe Cosmetics Program", "Facts via PubChem", "https://cscpsearch.cdph.ca.gov"
        ),
        Source(
            "ifra",
            "IFRA",
            "International Fragrance Association transparency list",
            "Facts via PubChem",
            "https://ifrafragrance.org",
        ),
        Source(
            "jecfa",
            "JECFA",
            "Joint FAO/WHO Expert Committee on Food Additives",
            "Facts via PubChem",
            "https://apps.who.int/food-additives-contaminants-jecfa-database/",
        ),
        Source(
            "eu_food",
            "EU",
            "EU Food Improvement Agents (European Commission)",
            "© European Union, reuse allowed",
            "https://food.ec.europa.eu/food-safety/food-improvement-agents_en",
        ),
        Source(
            "eu_pesticides",
            "EU",
            "EU Pesticides Database (European Commission)",
            "© European Union, reuse allowed",
            "https://food.ec.europa.eu/plants/pesticides/eu-pesticides-database_en",
        ),
        Source(
            "fda_greenbook",
            "FDA",
            "FDA Approved Animal Drug Products (Green Book)",
            PUBLIC_DOMAIN,
            "https://animaldrugsatfda.fda.gov",
        ),
        Source(
            "livertox",
            "LiverTox",
            "LiverTox (U.S. National Institutes of Health)",
            PUBLIC_DOMAIN,
            "https://www.ncbi.nlm.nih.gov/books/NBK547852/",
        ),
        Source(
            "lactmed",
            "LactMed",
            "Drugs and Lactation Database (U.S. National Library of Medicine)",
            PUBLIC_DOMAIN,
            "https://www.ncbi.nlm.nih.gov/books/NBK501922/",
        ),
        Source(
            "norman", "NORMAN", "NORMAN Suspect List Exchange", "CC BY 4.0", "https://www.norman-network.com/nds/SLE/"
        ),
        Source("t3db", "T3DB", "Toxin and Toxin Target Database", "Facts via PubChem", "http://www.t3db.ca"),
        Source(
            "niosh",
            "NIOSH",
            "National Institute for Occupational Safety and Health",
            PUBLIC_DOMAIN,
            "https://www.cdc.gov/niosh/",
        ),
        Source(
            "hakkinen",
            "Hakkinen",
            "Pertti (Bert) Hakkinen's toxicology annotations",
            "Facts via PubChem",
            "https://pubchem.ncbi.nlm.nih.gov/source/25876",
        ),
        Source(
            "usgs_cerc",
            "USGS",
            "USGS Columbia Environmental Research Center",
            PUBLIC_DOMAIN,
            "https://www.usgs.gov/centers/cerc",
        ),
        Source(
            "nist_maldi",
            "NIST",
            "NIST Synthetic Polymer MALDI Recipes Database",
            PUBLIC_DOMAIN,
            "https://maldi.nist.gov",
        ),
        Source(
            "chebi",
            "ChEBI",
            "ChEBI, Chemical Entities of Biological Interest (EMBL-EBI)",
            "CC BY 4.0",
            "https://www.ebi.ac.uk/chebi/",
        ),
        Source("wikidata", "Wikidata", "Wikidata, property P366 “has use”", "CC0", "https://www.wikidata.org"),
        Source(
            "atc",
            "WHO ATC",
            "WHO Anatomical Therapeutic Chemical classification (codes via Wikidata)",
            "Codes: CC0 (Wikidata)",
            "https://atcddd.fhi.no/atc_ddd_index/",
        ),
        Source(
            "jlab",
            "Jefferson Lab",
            "Jefferson Lab, U.S. Department of Energy (“It’s Elemental”)",
            "Facts via PubChem",
            "https://education.jlab.org/itselemental/",
        ),
        Source(
            "lanl",
            "LANL",
            "Los Alamos National Laboratory periodic table",
            "Facts via PubChem",
            "https://periodic.lanl.gov",
        ),
        Source(
            "iupac_isotopes",
            "IUPAC",
            "IUPAC Periodic Table of the Elements and Isotopes",
            "Facts via PubChem",
            "https://www.isotopesmatter.com",
        ),
        Source(
            "usgs_mcs",
            "USGS",
            "USGS Mineral Commodity Summaries",
            PUBLIC_DOMAIN,
            "https://www.usgs.gov/centers/national-minerals-information-center/mineral-commodity-summaries",
            quote=True,
        ),
    )
}

ALL = frozenset(SPHERE_IDS)
NO_MEDICINE = ALL - {"medicine"}
MEDICINE = frozenset({"medicine"})
FOOD = frozenset({"food"})
AGRICULTURE = frozenset({"agriculture"})
HOUSEHOLD = frozenset({"household"})


@dataclass(frozen=True)
class Rule:
    source: str
    context: Context


def _rule(source: str, **kwargs: object) -> Rule:
    return Rule(source, Context(**kwargs))  # type: ignore[arg-type]


HSDB = "Hazardous Substances Data Bank (HSDB)"
HAZMAP = "Haz-Map, Information on Hazardous Chemicals and Occupational Diseases"
NORMAN = "NORMAN Suspect List Exchange"
JECFA = "Joint FAO/WHO Expert Committee on Food Additives (JECFA)"
EU_FOOD = "EU Food Improvement Agents"
CIR = "Cosmetic Ingredient Review (CIR)"
CDR = "EPA Chemical Data Reporting (CDR)"
EU_PESTICIDES = "EU Pesticides Database"

# (PubChem heading, PubChem SourceName) → rule.
PUBCHEM_RULES: dict[tuple[str, str], Rule] = {
    ("Uses", HSDB): _rule("hsdb"),
    ("Uses", HAZMAP): _rule("hazmap", cue=True),
    ("Uses", "EPA Chemical and Products Database (CPDat)"): _rule("epa_cpdat", categories=True, spheres=NO_MEDICINE),
    ("Uses", CIR): _rule("cir", spheres=HOUSEHOLD, categories=True, default="cosmetics"),
    ("Uses", "Toxin and Toxin Target Database (T3DB)"): _rule("t3db", cue=True),
    ("Uses", NORMAN): _rule("norman"),
    ("Uses", "NIST Synthetic Polymer MALDI Recipes Database"): _rule(
        "nist_maldi", spheres=frozenset({"science"}), categories=True, default="analysis"
    ),
    ("Uses", "EPA Hazardous Air Pollutants"): _rule("epa_hap"),
    ("Uses", "The National Institute for Occupational Safety and Health (NIOSH)"): _rule("niosh"),
    ("Uses", "Pertti (Bert) Hakkinen's Toxicology and Other Annotations"): _rule("hakkinen", cue=True),
    ("Use Classification", NORMAN): _rule("norman", categories=True),
    ("Use Classification", JECFA): _rule("jecfa", spheres=FOOD, categories=True, default="food_additive"),
    ("Use Classification", "International Fragrance Association (IFRA)"): _rule(
        "ifra", spheres=HOUSEHOLD, categories=True, default="fragrance"
    ),
    ("Use Classification", "EPA Safer Choice"): _rule(
        "epa_saferchoice", spheres=frozenset({"household", "industry"}), categories=True, default="cleaning"
    ),
    ("Use Classification", "FDA Approved Animal Drug Products (Green Book)"): _rule(
        "fda_greenbook", spheres=MEDICINE, default="veterinary"
    ),
    ("Use Classification", "USGS Columbia Environmental Research Center"): _rule(
        "usgs_cerc", spheres=NO_MEDICINE, categories=True
    ),
    ("Use Classification", EU_FOOD): _rule("eu_food", spheres=FOOD, categories=True, default="food_additive"),
    ("Industry Uses", CDR): _rule("epa_cdr", spheres=NO_MEDICINE - {"defense"}, categories=True),
    ("Consumer Uses", CDR): _rule("epa_cdr", spheres=NO_MEDICINE - {"defense"}, categories=True),
    ("Therapeutic Uses", HSDB): _rule("hsdb", spheres=MEDICINE, categories=True, default="drug"),
    ("Drug Classes", "Drugs and Lactation Database (LactMed)"): _rule(
        "lactmed", spheres=MEDICINE, categories=True, default="drug"
    ),
    ("Drug Classes", "LiverTox"): _rule("livertox", spheres=MEDICINE, categories=True, default="drug"),
    ("Food Additive Classes", JECFA): _rule("jecfa", spheres=FOOD, categories=True, default="food_additive"),
    ("Food Additive Classes", EU_FOOD): _rule("eu_food", spheres=FOOD, categories=True, default="food_additive"),
    ("Agrochemical Category", EU_PESTICIDES): _rule(
        "eu_pesticides", spheres=AGRICULTURE, categories=True, default="pesticide"
    ),
    ("Agrochemical Category", "EPA Pesticide Ecotoxicity Database"): _rule(
        "epa_ecotox", spheres=AGRICULTURE, categories=True, default="pesticide"
    ),
    ("Agrochemical Category", NORMAN): _rule("norman", spheres=AGRICULTURE, categories=True, default="pesticide"),
    ("Pesticides", EU_PESTICIDES): _rule("eu_pesticides", spheres=AGRICULTURE, categories=True, default="pesticide"),
    ("Pesticides", NORMAN): _rule("norman", spheres=AGRICULTURE, categories=True, default="pesticide"),
    ("Pesticides", HAZMAP): _rule("hazmap", spheres=AGRICULTURE, categories=True, default="pesticide"),
    ("Cosmetics", CIR): _rule("cir", spheres=HOUSEHOLD, categories=True, default="cosmetics"),
    ("Cosmetics", NORMAN): _rule("norman", spheres=HOUSEHOLD, categories=True, default="cosmetics"),
    ("Cosmetics", "California Safe Cosmetics Program (CSCP) Product Database"): _rule(
        "cscp", spheres=HOUSEHOLD, categories=True, default="cosmetics"
    ),
}
PUBCHEM_HEADINGS: tuple[str, ...] = tuple(dict.fromkeys(heading for heading, _ in PUBCHEM_RULES))

# PubChem element pages: the last TOC heading → rule (any source under that heading).
ELEMENT_SOURCES = {
    "Jefferson Lab, U.S. Department of Energy": "jlab",
    "Los Alamos National Laboratory, U.S. Department of Energy": "lanl",
}
ISOTOPE_SOURCE = "iupac_isotopes"
ELEMENT_RULES: dict[str, Context] = {
    "Uses": Context(),
    "Isotopes in Medicine": Context(spheres=MEDICINE, default="nuclear_medicine"),
    "Isotopes in Industry": Context(spheres=ALL - MEDICINE, default="isotope_tracers"),
    "Isotopes in Earth/Planetary Science": Context(spheres=frozenset({"science"}), default="isotope_dating"),
    "Isotopes in Geochronology": Context(spheres=frozenset({"science"}), default="isotope_dating"),
    "Isotopes in Forensic Science and Anthropology": Context(spheres=frozenset({"science"}), default="isotope_tracers"),
    "Isotopes in Biology": Context(spheres=frozenset({"science", "medicine"}), default="isotope_tracers"),
}

CHEBI_CONTEXT = Context(spheres=NO_MEDICINE, categories=True)
WIKIDATA_CONTEXT = Context()
