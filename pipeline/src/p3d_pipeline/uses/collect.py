"""Collect uses of elements and compounds from checked sources (task U.2).

Sources, in the order they are read:

1. PubChem annotations by heading ("Uses", "Use Classification", "Therapeutic Uses"…):
   one request returns a page of 1 000 records for all compounds. Records come from
   HSDB, EPA, JECFA, FDA, EU databases and others; `registry.PUBCHEM_RULES` says how to
   read each of them.
2. PubChem element pages: "Uses" texts of Los Alamos and Jefferson Lab, isotope uses.
3. ChEBI application roles (herbicide, food colouring, refrigerant…), via the ChEBI IDs
   of Wikidata (P683).
4. Wikidata: ATC codes of medicines (P267) and "has use" (P366).
5. USGS Mineral Commodity Summaries: shares of end uses for mineral commodities,
   curated by hand into usgs_end_uses.json (elements only).

Every use on the card is a vocabulary term with the list of sources that support it.
"""

from __future__ import annotations

import gzip
import io
import json
import logging
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from ..sources import wikidata
from .match import Hit, Matcher
from .registry import (
    CHEBI_CONTEXT,
    ELEMENT_RULES,
    ELEMENT_SOURCES,
    ISOTOPE_SOURCE,
    PUBCHEM_HEADINGS,
    PUBCHEM_RULES,
    SOURCES,
    WIKIDATA_CONTEXT,
)
from .vocabulary import SPHERE_IDS, SPHERES, TERM_BY_ID, TERMS, atc_term

if TYPE_CHECKING:
    from ..http import Fetcher

log = logging.getLogger("p3d.uses")

ANNOTATIONS = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/annotations/heading/{}/JSON"
ELEMENT_RECORD = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/element/{}/JSON"
CHEBI_OBO = "https://ftp.ebi.ac.uk/pub/databases/chebi/ontology/chebi_core.obo.gz"
CHEBI_APPLICATION = "CHEBI:33232"
CHEBI_PHARMACEUTICAL = "CHEBI:52217"
HAS_ROLE = ("relationship: has_role CHEBI:", "relationship: RO:0000087 CHEBI:")
MAX_PAGES = 200
QUOTES_PER_SUBSTANCE = 2
QUOTE_MIN, QUOTE_MAX = 40, 320
USGS_FILE = Path(__file__).with_name("usgs_end_uses.json")


def pubchem_compound_url(cid: int, heading: str) -> str:
    return f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}#section={heading.replace(' ', '-')}"


def pubchem_element_url(z: int, heading: str) -> str:
    return f"https://pubchem.ncbi.nlm.nih.gov/element/{z}#section={heading.replace(' ', '-').replace('/', '-')}"


@dataclass
class Evidence:
    term: str
    source: str
    url: str
    sentence: str | None = None


@dataclass
class Uses:
    """What the sources say about one substance (a compound QID or an element QID)."""

    evidence: list[Evidence] = field(default_factory=list)
    notes: set[str] = field(default_factory=set)
    shares: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Collector:
    fetcher: Fetcher
    matcher: Matcher = field(default_factory=Matcher)
    uses: dict[str, Uses] = field(default_factory=lambda: defaultdict(Uses))
    stats: Counter[str] = field(default_factory=Counter)

    # ------------------------------------------------------------------ helpers
    def _add(self, key: str, hits: Iterable[Hit], source: str, url: str) -> None:
        for hit in hits:
            self.uses[key].evidence.append(Evidence(hit.term, source, url, hit.sentence))
            self.stats[f"evidence:{source}"] += 1

    # ------------------------------------------------------------------ PubChem annotations
    def _pages(self, heading: str) -> Iterator[dict[str, Any]]:
        url = ANNOTATIONS.format(quote(heading))
        page, total = 1, 1
        while page <= min(total, MAX_PAGES):
            try:
                body = self.fetcher.get(url, {"heading_type": "Compound", "page": str(page)}, attempts=6)
            except Exception as error:  # one lost page must not stop the build
                log.warning("PubChem %s page %d: %s", heading, page, error)
                self.stats["pubchem_pages_failed"] += 1
                page += 1
                continue
            if body is None:
                break
            data = json.loads(body).get("Annotations", {})
            total = int(data.get("TotalPages", 1))
            self.stats["pubchem_pages"] += 1
            yield from data.get("Annotation", []) or []
            page += 1

    def pubchem_annotations(self, cids: dict[int, list[str]]) -> None:
        for heading in PUBCHEM_HEADINGS:
            log.info("Uses: PubChem %s", heading)
            for annotation in self._pages(heading):
                source_name = annotation.get("SourceName", "")
                rule = PUBCHEM_RULES.get((heading, source_name))
                linked = [int(cid) for cid in (annotation.get("LinkedRecords", {}).get("CID") or [])]
                targets = [(key, cid) for cid in linked for key in cids.get(cid, [])]
                if not targets:
                    continue
                if rule is None:
                    self.stats[f"skipped:{heading}:{source_name}"] += 1
                    continue
                strings = [
                    item.get("String", "")
                    for data in annotation.get("Data", []) or []
                    for item in (data.get("Value", {}).get("StringWithMarkup") or [])
                ]
                if rule.source == "eu_pesticides":
                    self._eu_status(strings, [key for key, _ in targets])
                hits = self.matcher.find(strings, rule.context)
                for key, cid in targets:
                    self._add(key, hits, rule.source, pubchem_compound_url(cid, heading))

    def _eu_status(self, strings: list[str], keys: list[str]) -> None:
        for text in strings:
            status = re.search(r"EU Pesticides database:\s*(Not approved|Approved|Pending)", text, re.IGNORECASE)
            if status:
                for key in keys:
                    if status.group(1).lower() == "not approved":
                        self.uses[key].notes.add("eu_not_approved")
                    else:
                        self.uses[key].notes.add("eu_approved")

    # ------------------------------------------------------------------ PubChem element pages
    def element_pages(self, elements: list[dict[str, Any]]) -> None:
        log.info("Uses: PubChem element pages")
        for element in elements:
            key = element.get("wikidata")
            if not key:
                continue
            try:
                body = self.fetcher.get(ELEMENT_RECORD.format(element["z"]), attempts=6)
            except Exception as error:
                log.warning("PubChem element %s: %s", element["symbol"], error)
                self.stats["element_pages_failed"] += 1
                continue
            if body is None:
                continue
            record = json.loads(body).get("Record", {})
            references = {ref.get("ReferenceNumber"): ref.get("SourceName", "") for ref in record.get("Reference", [])}
            for heading, information in _element_information(record):
                context = ELEMENT_RULES.get(heading)
                if context is None:
                    continue
                source_name = references.get(information.get("ReferenceNumber"), "")
                source = ELEMENT_SOURCES.get(source_name) if heading == "Uses" else ISOTOPE_SOURCE
                if source is None:
                    self.stats[f"skipped:element:{heading}:{source_name}"] += 1
                    continue
                strings = [item.get("String", "") for item in information.get("Value", {}).get("StringWithMarkup", [])]
                hits = self.matcher.find(strings, context)
                self._add(key, hits, source, pubchem_element_url(element["z"], heading))

    # ------------------------------------------------------------------ ChEBI
    def chebi_roles(self, chebi_ids: dict[str, set[str]]) -> None:
        log.info("Uses: ChEBI application roles")
        try:
            body = self.fetcher.get(CHEBI_OBO, attempts=4)
        except Exception as error:
            log.warning("ChEBI: %s", error)
            self.stats["chebi_failed"] += 1
            return
        if body is None:
            self.stats["chebi_failed"] += 1
            return
        ontology = ChebiOntology.parse(gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body)
        memo: dict[str, list[str]] = {}
        for key, ids in chebi_ids.items():
            for raw in ids:
                chebi = raw if raw.startswith("CHEBI:") else f"CHEBI:{raw}"
                for role in ontology.application_roles(chebi):
                    if role not in memo:
                        memo[role] = self._chebi_terms(ontology, role)
                    url = f"https://www.ebi.ac.uk/chebi/searchId.do?chebiId={chebi}"
                    self._add(key, (Hit(term, ontology.names.get(role)) for term in memo[role]), "chebi", url)

    def _chebi_terms(self, ontology: ChebiOntology, role: str) -> list[str]:
        """Terms for a role: its own name first, then the names of its ancestors."""
        for candidate in ontology.lineage(role):
            name = ontology.names.get(candidate, "")
            terms = self.matcher.sentence_terms(name, CHEBI_CONTEXT)
            if terms:
                return terms
        return []

    # ------------------------------------------------------------------ Wikidata
    def wikidata_uses(self, uses: dict[str, set[str]], atc: dict[str, set[str]]) -> None:
        log.info("Uses: Wikidata P366 and ATC")
        use_ids = {wikidata.qid(value) for values in uses.values() for value in values}
        labels = wikidata.fetch_labels(self.fetcher, use_ids, ("en",)) if use_ids else {}
        terms_of: dict[str, list[str]] = {}
        for use in use_ids:
            label = labels.get(use, {}).get("en", "")
            terms_of[use] = self.matcher.sentence_terms(label, WIKIDATA_CONTEXT) if label else []
        for key, values in uses.items():
            for value in values:
                use_id = wikidata.qid(value)
                use_label = labels.get(use_id, {}).get("en")
                hits = [Hit(term, use_label) for term in terms_of.get(use_id, [])]
                self._add(key, hits, "wikidata", f"https://www.wikidata.org/wiki/{key}#P366")
        for key, codes in atc.items():
            for code in codes:
                term = atc_term(code)
                if term:
                    self._add(key, [Hit(term, code)], "atc", f"https://atcddd.fhi.no/atc_ddd_index/?code={code}")

    # ------------------------------------------------------------------ USGS
    def usgs_shares(
        self,
        elements: list[dict[str, Any]],
        compound_names: dict[str, list[str]],
        path: Path = USGS_FILE,
    ) -> None:
        """End-use shares of mineral commodities, curated from USGS (see tools/probe/usgs_curate.py)."""
        if not path.is_file():
            return
        curated = json.loads(path.read_text(encoding="utf-8"))
        qid_by_symbol = {element["symbol"]: element.get("wikidata") for element in elements}
        for entry in curated.get("commodities", []):
            keys = [qid_by_symbol.get(symbol) for symbol in entry["elements"]]
            keys += [key for name in entry.get("compounds", []) for key in compound_names.get(name.lower(), [])]
            terms = [item["term"] for item in entry["shares"] if item.get("term")] + entry.get("terms", [])
            for key in dict.fromkeys(key for key in keys if key):
                self._add(key, [Hit(term, None) for term in dict.fromkeys(terms)], "usgs_mcs", entry["url"])
                if not entry["shares"]:
                    self.uses[key].evidence.append(Evidence("", "usgs_mcs", entry["url"], entry["quote"]))
                    continue
                self.uses[key].shares.append(
                    {
                        "source": "usgs_mcs",
                        "commodity": entry["commodity"],
                        "edition": entry["edition"],
                        "year": entry["year"],
                        "scope": entry["scope"],
                        "ranked": entry["ranked"],
                        "group": len(entry["elements"]) > 1,
                        "url": entry["url"],
                        "quote": entry["quote"],
                        "items": entry["shares"],
                    }
                )


def _element_information(record: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    def walk(section: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
        heading = section.get("TOCHeading", "")
        for information in section.get("Information", []) or []:
            yield heading, information
        for child in section.get("Section", []) or []:
            yield from walk(child)

    for section in record.get("Section", []) or []:
        yield from walk(section)


@dataclass
class ChebiOntology:
    names: dict[str, str]
    parents: dict[str, set[str]]
    roles: dict[str, set[str]]
    _ancestors: dict[str, set[str]] = field(default_factory=dict)

    @classmethod
    def parse(cls, data: bytes) -> ChebiOntology:
        names: dict[str, str] = {}
        parents: dict[str, set[str]] = defaultdict(set)
        roles: dict[str, set[str]] = defaultdict(set)
        current: str | None = None
        for raw in io.StringIO(data.decode("utf-8", "replace")):
            line = raw.strip()
            if line.startswith("["):
                current = None
            elif line.startswith("id: CHEBI:"):
                current = line[4:]
            elif current and line.startswith("name: "):
                names[current] = line[6:]
            elif current and line.startswith("is_a: CHEBI:"):
                parents[current].add(line[6:].split()[0])
            elif current and line.startswith(HAS_ROLE):
                roles[current].add(line.split()[2])
        return cls(names, dict(parents), dict(roles))

    def ancestors(self, term: str) -> set[str]:
        if term not in self._ancestors:
            self._ancestors[term] = set()  # cycle guard
            result: set[str] = set()
            for parent in self.parents.get(term, ()):
                result |= {parent} | self.ancestors(parent)
            self._ancestors[term] = result
        return self._ancestors[term]

    def lineage(self, term: str) -> list[str]:
        """The term and its ancestors, nearest first, up to (not including) "application"."""
        order, frontier, seen = [], [term], {term}
        while frontier:
            order += frontier
            following = []
            for item in frontier:
                for parent in sorted(self.parents.get(item, ())):
                    if parent not in seen and parent != CHEBI_APPLICATION:
                        seen.add(parent)
                        following.append(parent)
            frontier = following
        return order

    def application_roles(self, chebi: str) -> list[str]:
        """Roles of a substance that are applications, without the pharmaceutical branch."""
        found = []
        for role in sorted(self.roles.get(chebi, ())):
            lineage = self.ancestors(role) | {role}
            if CHEBI_APPLICATION in lineage and CHEBI_PHARMACEUTICAL not in lineage:
                found.append(role)
        return found


# ---------------------------------------------------------------------------- card
SPHERE_ORDER = {sphere: index for index, sphere in enumerate(SPHERE_IDS)}
TERM_ORDER = {term.id: index for index, term in enumerate(TERMS)}
_UPPER = re.compile(r"[A-Z]")
_LETTERS = re.compile(r"[A-Za-z]")


def _good_quote(sentence: str, source: str) -> bool:
    if source == "usgs_mcs":  # curated by hand
        return True
    letters = len(_LETTERS.findall(sentence))
    return (
        QUOTE_MIN <= len(sentence) <= QUOTE_MAX
        and letters > 0
        and len(_UPPER.findall(sentence)) / letters < 0.25
        and " " in sentence
    )


def card(uses: Uses) -> dict[str, Any] | None:
    """The `uses` field of an element or compound card, or None without evidence."""
    by_term: dict[str, list[Evidence]] = defaultdict(list)
    for evidence in uses.evidence:
        if evidence.term in TERM_BY_ID:
            by_term[evidence.term].append(evidence)
    if not by_term:
        return None
    # A general term ("Pesticides") gives way to a specific one ("Herbicides").
    groups = {TERM_BY_ID[term_id].group for term_id in by_term if TERM_BY_ID[term_id].group}
    for term_id in list(by_term):
        umbrella = TERM_BY_ID[term_id].umbrella
        if umbrella and umbrella in groups:
            del by_term[term_id]

    sources: dict[str, str] = {}  # source id → URL for this substance
    spheres: dict[str, list[dict[str, Any]]] = defaultdict(list)
    weight: Counter[str] = Counter()
    for term_id, items in by_term.items():
        term = TERM_BY_ID[term_id]
        term_sources = list(dict.fromkeys(item.source for item in items))
        for item in items:
            sources.setdefault(item.source, item.url)
        entry: dict[str, Any] = {"id": term_id, "names": term.names, "sources": term_sources}
        pesticide = "pesticide" in (term.group, term.umbrella)
        if pesticide and "eu_not_approved" in uses.notes and "eu_approved" not in uses.notes:
            entry["notes"] = ["eu_not_approved"]
        share = next(
            (
                item["share"]
                for block in uses.shares
                for item in block["items"]
                if item.get("term") == term_id and item.get("share") is not None
            ),
            None,
        )
        if share is not None:
            entry["share"] = share
        spheres[term.sphere].append(entry)
        weight[term.sphere] += len(term_sources)
    for entries in spheres.values():
        entries.sort(key=lambda entry: (-len(entry["sources"]), -entry.get("share", 0), TERM_ORDER[entry["id"]]))

    quotes: list[dict[str, str]] = []
    candidates = [
        evidence
        for evidence in uses.evidence
        if evidence.sentence and SOURCES[evidence.source].quote and _good_quote(evidence.sentence, evidence.source)
    ]
    covered: Counter[str] = Counter(evidence.sentence or "" for evidence in candidates if evidence.term)
    candidates.sort(key=lambda e: (e.source != "usgs_mcs", -covered[e.sentence or ""], e.sentence or ""))
    for evidence in candidates:
        text = evidence.sentence or ""
        if any(quote["text"] == text for quote in quotes):
            continue
        quotes.append({"source": evidence.source, "text": text if text.endswith(".") else text + "."})
        sources.setdefault(evidence.source, evidence.url)
        if len(quotes) >= QUOTES_PER_SUBSTANCE:
            break

    result: dict[str, Any] = {
        "spheres": [
            {"id": sphere, "terms": spheres[sphere]}
            for sphere in sorted(spheres, key=lambda sphere: (-weight[sphere], SPHERE_ORDER[sphere]))
        ],
        "sources": [
            {
                "id": source,
                "short": SOURCES[source].short,
                "name": SOURCES[source].name,
                "url": url,
                "license": SOURCES[source].license,
            }
            for source, url in sources.items()
        ],
    }
    if quotes:
        result["quotes"] = quotes
    if uses.shares:
        result["shares"] = uses.shares
    return result


def vocabulary() -> dict[str, Any]:
    """The vocabulary and the sources, written next to the dataset (uses.json)."""
    return {
        "spheres": [{"id": sphere.id, "names": sphere.names} for sphere in SPHERES],
        "terms": [{"id": term.id, "sphere": term.sphere, "names": term.names} for term in TERMS],
        "sources": [
            {"id": s.id, "short": s.short, "name": s.name, "license": s.license, "url": s.homepage}
            for s in SOURCES.values()
        ],
    }


def collect(
    fetcher: Fetcher,
    compounds: list[tuple[str, int | None, str]],
    elements: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], Counter[str]]:
    """Uses cards by QID (compounds and elements) and collection statistics.

    compounds: (QID, PubChem CID, English name) of every compound in the dataset.
    """
    collector = Collector(fetcher)
    element_qids = {element["wikidata"] for element in elements if element.get("wikidata")}
    cids: dict[int, list[str]] = defaultdict(list)
    names: dict[str, list[str]] = defaultdict(list)
    for key, cid, name in compounds:
        if cid:
            cids[cid].append(key)
        if name:
            names[name.lower()].append(key)
    element_cids: dict[str, set[str]] = {}
    try:
        element_cids = wikidata.fetch_item_values(fetcher, element_qids, "wdt:P662")
    except Exception as error:
        log.warning("Wikidata element CIDs: %s", error)
    for key, cid_values in element_cids.items():
        for value in cid_values:
            if value.isdigit():
                cids[int(value)].append(key)

    collector.pubchem_annotations(cids)
    collector.element_pages(elements)

    def property_values(predicate: str) -> dict[str, set[str]]:
        try:
            found = wikidata.fetch_selection_values(fetcher, predicate)
            for key, items in wikidata.fetch_item_values(fetcher, element_qids, predicate).items():
                found.setdefault(key, set()).update(items)
            return found
        except Exception as error:  # an outage must not stop a build from the cache
            log.warning("Wikidata %s: %s", predicate, error)
            collector.stats[f"wikidata_failed:{predicate}"] += 1
            return {}

    collector.chebi_roles(property_values("wdt:P683"))
    collector.wikidata_uses(property_values("wdt:P366"), property_values("wdt:P267"))
    collector.usgs_shares(elements, names)

    cards: dict[str, dict[str, Any]] = {}
    for key, uses in collector.uses.items():
        result = card(uses)
        if result:
            cards[key] = result
    collector.stats["cards"] = len(cards)
    return cards, collector.stats


def report_lines(
    cards: dict[str, dict[str, Any]],
    stats: Counter[str],
    compounds: list[tuple[str, str]],
    elements: list[dict[str, Any]],
) -> list[str]:
    """Report section: coverage by sphere and source, and the uses of reference substances."""
    compound_ids = {key for key, _ in compounds}
    element_ids = {element["wikidata"] for element in elements if element.get("wikidata")}
    with_compounds = [key for key in cards if key in compound_ids]
    with_elements = [key for key in cards if key in element_ids]
    spheres: Counter[str] = Counter()
    terms: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    for key in with_compounds:
        for sphere in cards[key]["spheres"]:
            spheres[sphere["id"]] += 1
            for term in sphere["terms"]:
                terms[term["id"]] += 1
        for source in cards[key]["sources"]:
            sources[source["id"]] += 1
    lines = [
        "",
        "## Применение веществ (U.2)",
        "",
        f"- Соединений с применением: {len(with_compounds)} из {len(compound_ids)}.",
        f"- Элементов с применением: {len(with_elements)} из {len(element_ids)}; "
        f"с долями USGS: {sum(1 for key in with_elements if cards[key].get('shares'))}.",
        f"- Страниц PubChem прочитано: {stats['pubchem_pages']}; не удалось: {stats['pubchem_pages_failed']}.",
        "",
        "| Сфера | Соединений |",
        "| --- | --- |",
    ]
    names = {sphere.id: sphere.names["ru"] for sphere in SPHERES}
    lines += [f"| {names[sphere]} | {count} |" for sphere, count in spheres.most_common()]
    lines += ["", "| Источник | Соединений |", "| --- | --- |"]
    lines += [f"| {SOURCES[source].name} | {count} |" for source, count in sources.most_common()]
    lines += ["", "### Самые частые применения", ""]
    lines += [f"- {TERM_BY_ID[term].names['ru']}: {count}" for term, count in terms.most_common(40)]
    skipped = [(key, count) for key, count in stats.items() if key.startswith("skipped:")]
    if skipped:
        lines += ["", "### Пропущенные источники (нет правила чтения)", ""]
        lines += [f"- {key[8:]}: {count}" for key, count in sorted(skipped, key=lambda item: -item[1])[:30]]
    lines += ["", "### Эталонные вещества", ""]
    by_name = {name.lower(): key for key, name in compounds}
    references = [(by_name.get(name, ""), name) for name in REFERENCE_COMPOUNDS]
    references += [
        (element["wikidata"], element["names"]["en"])
        for element in elements
        if element["symbol"] in REFERENCE_ELEMENTS and element.get("wikidata")
    ]
    for key, name in references:
        uses = cards.get(key)
        if not uses:
            lines.append(f"- {name}: нет данных")
            continue
        parts = [
            f"{names[sphere['id']]}: "
            + ", ".join(f"{term['names']['ru']} ({', '.join(term['sources'])})" for term in sphere["terms"])
            for sphere in uses["spheres"]
        ]
        lines.append(f"- **{name}** — " + "; ".join(parts))
    return lines


# Reference substances listed in the report (English names as in the dataset).
REFERENCE_COMPOUNDS = (
    "water",
    "ethanol",
    "caffeine",
    "aspirin",
    "sodium chloride",
    "potassium nitrate",
    "ammonium nitrate",
    "ddt",
    "glyphosate",
    "paracetamol",
    "titanium dioxide",
    "sulfuric acid",
)
REFERENCE_ELEMENTS = ("H", "He", "Li", "C", "Fe", "Cu", "Si", "U", "Pu", "I")
