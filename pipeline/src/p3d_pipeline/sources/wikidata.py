"""Wikidata via the QLever SPARQL endpoint (fast, no 60-second timeout).

Selection rule (ADR 0004): items with a chemical formula (P274) and an article in
the English, Russian or Ukrainian Wikipedia.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import unquote

from ..http import Fetcher

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
    }
    for kind, predicate in identifier_queries.items():
        rows = sparql(
            fetcher,
            f"""SELECT DISTINCT ?item ?value WHERE {{
              ?item wdt:P274 ?formula ; {predicate} ?value . {_HAS_ARTICLE}
            }}""",
        )
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
    return records
