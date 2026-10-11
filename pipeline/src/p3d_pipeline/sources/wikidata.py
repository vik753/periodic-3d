"""Wikidata via the QLever SPARQL endpoint (fast, no 60-second timeout).

Selection rule (ADR 0004): items with a chemical formula (P274) and an article in
the English, Russian or Ukrainian Wikipedia.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from urllib.parse import unquote

from ..http import Fetcher

log = logging.getLogger("p3d.wikidata")

QLEVER = "https://qlever.cs.uni-freiburg.de/api/wikidata"

PREFIXES = """PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wikibase: <http://wikiba.se/ontology#>
PREFIX schema: <http://schema.org/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
"""

WIKIS: dict[str, str] = {
    "en": "https://en.wikipedia.org/",
    "ru": "https://ru.wikipedia.org/",
    "uk": "https://uk.wikipedia.org/",
}
LANGUAGES = tuple(WIKIS)
_WIKI_VALUES = " ".join(f"<{iri}>" for iri in WIKIS.values())
_HAS_ARTICLE = f"?article schema:about ?item ; schema:isPartOf ?wiki . VALUES ?wiki {{ {_WIKI_VALUES} }}"


def qid(iri: str) -> str:
    return iri.rsplit("/", 1)[-1]


def sparql(fetcher: Fetcher, query: str) -> list[dict[str, str]]:
    """Run a SELECT query and return rows as {variable: value} dicts."""
    body = fetcher.get(QLEVER, {"query": PREFIXES + query}, accept="application/sparql-results+json")
    if body is None:
        raise RuntimeError("QLever returned no result")
    data = json.loads(body)
    return [{name: cell["value"] for name, cell in row.items()} for row in data["results"]["bindings"]]


@dataclass
class ElementLabels:
    qid: str
    z: int
    labels: dict[str, str] = field(default_factory=dict)


def commons_file_name(value: str) -> str:
    """'http://commons.wikimedia.org/wiki/Special:FilePath/Iron%20cube.jpg' → 'Iron cube.jpg'."""
    return unquote(value.rsplit("/", 1)[-1]).replace("_", " ")


def fetch_element_images(fetcher: Fetcher) -> dict[int, str]:
    """Photo of each element (P18), by atomic number. Empty when the query fails."""
    try:
        rows = sparql(
            fetcher,
            """SELECT ?z ?image WHERE {
              ?item wdt:P31 wd:Q11344 ; wdt:P1086 ?z ; wdt:P18 ?image .
            }""",
        )
    except Exception as error:
        log.warning("Wikidata element images skipped: %s", error)
        return {}
    images: dict[int, str] = {}
    for row in rows:
        z = round(float(row["z"]))
        name = commons_file_name(row["image"])
        if 1 <= z <= 118 and (z not in images or name < images[z]):
            images[z] = name
    return images


def fetch_element_labels(fetcher: Fetcher) -> dict[int, ElementLabels]:
    rows = sparql(
        fetcher,
        """SELECT ?item ?z ?label ?lang WHERE {
          ?item wdt:P31 wd:Q11344 ; wdt:P1086 ?z .
          ?item rdfs:label ?label .
          BIND(LANG(?label) AS ?lang)
          FILTER(?lang IN ("en", "ru", "uk", "la"))
        }""",
    )
    result: dict[int, ElementLabels] = {}
    for row in rows:
        z = round(float(row["z"]))
        if not 1 <= z <= 118:
            continue
        entry = result.setdefault(z, ElementLabels(qid=qid(row["item"]), z=z))
        entry.labels[row["lang"]] = row["label"]
    return result


@dataclass
class CompoundRecord:
    qid: str
    formulas: set[str] = field(default_factory=set)
    articles: dict[str, str] = field(default_factory=dict)  # language → article title
    sitelinks: int = 0
    labels: dict[str, str] = field(default_factory=dict)
    cids: set[int] = field(default_factory=set)
    inchikeys: set[str] = field(default_factory=set)
    classes: set[str] = field(default_factory=set)
    mp_ids: set[str] = field(default_factory=set)
    smiles: set[str] = field(default_factory=set)  # isomeric (P2017)
    canonical_smiles: set[str] = field(default_factory=set)  # P233
    images: set[str] = field(default_factory=set)  # Commons file names (P18)

    @property
    def best_smiles(self) -> str | None:
        """Isomeric SMILES first (it keeps stereochemistry), then canonical; shortest wins."""
        for options in (self.smiles, self.canonical_smiles):
            if options:
                return min(options, key=lambda value: (len(value), value))
        return None


def _article_title(iri: str) -> str:
    return unquote(iri.split("/wiki/", 1)[-1]).replace("_", " ")


def fetch_compounds(fetcher: Fetcher) -> dict[str, CompoundRecord]:
    """All compounds with a formula and a ru/uk/en Wikipedia article."""
    records: dict[str, CompoundRecord] = {}

    def record(iri: str) -> CompoundRecord:
        key = qid(iri)
        if key not in records:
            records[key] = CompoundRecord(qid=key)
        return records[key]

    for row in sparql(
        fetcher,
        f"""SELECT ?item ?formula ?article ?wiki ?sitelinks WHERE {{
          ?item wdt:P274 ?formula . {_HAS_ARTICLE}
          OPTIONAL {{ ?item wikibase:sitelinks ?sitelinks }}
        }}""",
    ):
        entry = record(row["item"])
        entry.formulas.add(row["formula"])
        for language, iri in WIKIS.items():
            if row["wiki"] == iri:
                entry.articles[language] = _article_title(row["article"])
        if "sitelinks" in row:
            entry.sitelinks = max(entry.sitelinks, round(float(row["sitelinks"])))

    for row in sparql(
        fetcher,
        f"""SELECT DISTINCT ?item ?label ?lang WHERE {{
          ?item wdt:P274 ?formula . {_HAS_ARTICLE}
          ?item rdfs:label ?label .
          BIND(LANG(?label) AS ?lang)
          FILTER(?lang IN ("en", "ru", "uk"))
        }}""",
    ):
        if (labelled := records.get(qid(row["item"]))) is not None:
            labelled.labels[row["lang"]] = row["label"]

    identifier_queries = {
        "cid": "wdt:P662",
        "inchikey": "wdt:P235",
        "class": "wdt:P31",
        "mp": "wdt:P9902",
        "smiles": "wdt:P2017",
        "canonical_smiles": "wdt:P233",
        "image": "wdt:P18",
    }
    optional = {"smiles", "canonical_smiles", "image"}  # added later: an outage must not stop a build from the cache
    for kind, predicate in identifier_queries.items():
        query = f"""SELECT DISTINCT ?item ?value WHERE {{
              ?item wdt:P274 ?formula ; {predicate} ?value . {_HAS_ARTICLE}
            }}"""
        try:
            rows = sparql(fetcher, query)
        except Exception as error:
            if kind not in optional:
                raise
            log.warning("Wikidata %s skipped: %s", kind, error)
            continue
        for row in rows:
            target = records.get(qid(row["item"]))
            if target is None:
                continue
            value = row["value"]
            if kind == "cid" and value.isdigit():
                target.cids.add(int(value))
            elif kind == "inchikey":
                target.inchikeys.add(value)
            elif kind == "class":
                target.classes.add(qid(value))
            elif kind == "mp":
                target.mp_ids.add(value)
            elif kind == "smiles":
                target.smiles.add(value)
            elif kind == "canonical_smiles":
                target.canonical_smiles.add(value)
            elif kind == "image":
                target.images.add(commons_file_name(value))
    return records


LABEL_BATCH = 300


def fetch_labels(fetcher: Fetcher, qids: set[str], languages: tuple[str, ...] = LANGUAGES) -> dict[str, dict[str, str]]:
    """Labels of arbitrary items (for example compound classes) in the given languages."""
    result: dict[str, dict[str, str]] = {}
    ordered = sorted(qids)
    language_list = ", ".join(f'"{language}"' for language in languages)
    for start in range(0, len(ordered), LABEL_BATCH):
        values = " ".join(f"wd:{item}" for item in ordered[start : start + LABEL_BATCH])
        rows = sparql(
            fetcher,
            f"""SELECT ?item ?label ?lang WHERE {{
              VALUES ?item {{ {values} }}
              ?item rdfs:label ?label .
              BIND(LANG(?label) AS ?lang)
              FILTER(?lang IN ({language_list}))
            }}""",
        )
        for row in rows:
            result.setdefault(qid(row["item"]), {})[row["lang"]] = row["label"]
    return result
