"""Probe: ChEBI application roles for our compounds (task U.1).

ChEBI (EMBL-EBI, CC BY 4.0) curates "has role" links; roles under "application"
(CHEBI:33232) say what a substance is used for: herbicide, food colouring, fuel... This
script reads chebi_lite.obo, takes the ChEBI IDs of our compounds from Wikidata (P683)
and reports how many have an application role and which roles are common.

Usage: python3 tools/probe/chebi_roles.py <out-dir>
"""

from __future__ import annotations

import gzip
import io
import json
import sys
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

OBO_URLS = [
    "https://ftp.ebi.ac.uk/pub/databases/chebi/ontology/chebi_core.obo.gz",
    "https://ftp.ebi.ac.uk/pub/databases/chebi/ontology/chebi.obo.gz",
    "http://purl.obolibrary.org/obo/chebi.obo",
]
# "has role": the name in older files, the Relation Ontology ID in newer ones.
HAS_ROLE = ("relationship: has_role CHEBI:", "relationship: RO:0000087 CHEBI:")
QLEVER = "https://qlever.cs.uni-freiburg.de/api/wikidata"
QUERY = """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX schema: <http://schema.org/>
SELECT ?item ?chebi ?element WHERE {
  { ?item wdt:P274 ?formula .
    ?article schema:about ?item ; schema:isPartOf ?wiki .
    VALUES ?wiki { <https://en.wikipedia.org/> <https://ru.wikipedia.org/> <https://uk.wikipedia.org/> } }
  UNION { ?item wdt:P31 <http://www.wikidata.org/entity/Q11344> . BIND(1 AS ?element) }
  ?item wdt:P683 ?chebi .
}"""
APPLICATION = "CHEBI:33232"
AGENT = "http"


def fetch(url: str, accept: str | None = None) -> bytes:
    headers = {"User-Agent": "periodic-3d probe (github.com/vik753/periodic-3d)"}
    if accept:
        headers["Accept"] = accept
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=600) as response:
        return response.read()


def load_obo() -> tuple[dict[str, str], dict[str, set[str]], dict[str, set[str]]]:
    for url in OBO_URLS:
        try:
            data = fetch(url)
            print(f"ChEBI: {url} ({len(data) // 1_000_000} MB)")
            break
        except Exception as error:  # try the next mirror
            print(f"{url}: {error}")
    else:
        raise SystemExit("ChEBI ontology not reachable")
    if data[:2] == b"\x1f\x8b":
        data = gzip.decompress(data)
    names: dict[str, str] = {}
    parents: dict[str, set[str]] = defaultdict(set)
    roles: dict[str, set[str]] = defaultdict(set)
    current = None
    for raw in io.StringIO(data.decode("utf-8", "replace")):
        line = raw.strip()
        if line == "[Term]":
            current = None
        elif line.startswith("id: CHEBI:"):
            current = line[4:]
        elif current and line.startswith("name: "):
            names[current] = line[6:]
        elif current and line.startswith("is_a: CHEBI:"):
            parents[current].add(line[6:].split()[0])
        elif current and line.startswith(HAS_ROLE):
            roles[current].add(line.split()[2])
    print(f"ChEBI: {len(names)} terms, {sum(len(v) for v in roles.values())} role links")
    return names, parents, roles


def ancestors(term: str, parents: dict[str, set[str]], memo: dict[str, set[str]]) -> set[str]:
    if term in memo:
        return memo[term]
    memo[term] = set()
    result: set[str] = set()
    for parent in parents.get(term, ()):
        result.add(parent)
        result |= ancestors(parent, parents, memo)
    memo[term] = result
    return result


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    names, parents, roles = load_obo()
    body = fetch(QLEVER + "?" + urllib.parse.urlencode({"query": QUERY}), "application/sparql-results+json")
    rows = json.loads(body)["results"]["bindings"]
    ours: dict[str, str] = {}
    elements: set[str] = set()
    for row in rows:
        chebi = "CHEBI:" + row["chebi"]["value"].removeprefix("CHEBI:")
        ours[chebi] = row["item"]["value"].rsplit("/", 1)[-1]
        if "element" in row:
            elements.add(chebi)
    memo: dict[str, set[str]] = {}
    applied: Counter[str] = Counter()
    covered = 0
    covered_elements = 0
    examples: list[str] = []
    for chebi, item in ours.items():
        found = {role for role in roles.get(chebi, ()) if APPLICATION in ancestors(role, parents, memo)}
        if found:
            covered += 1
            covered_elements += chebi in elements
            applied.update(found)
            if len(examples) < 40:
                examples.append(f"{item} {names.get(chebi, chebi)}: " + ", ".join(names.get(r, r) for r in sorted(found)))
    top_level = Counter()
    for role, count in applied.items():
        chain = ancestors(role, parents, memo)
        for parent in parents.get(APPLICATION, set()) | {APPLICATION}:
            pass
        direct = [a for a in chain if APPLICATION in parents.get(a, set())] or [role]
        for a in direct:
            top_level[names.get(a, a)] += count
    lines = [
        "# Probe: ChEBI application roles",
        "",
        f"- Our Wikidata items with a ChEBI ID: {len(ours)} (elements: {len(elements)})",
        f"- With an application role: {covered} (elements: {covered_elements})",
        "",
        "## Top-level application branches",
        "",
    ]
    lines += [f"- {name}: {count}" for name, count in top_level.most_common(40)]
    lines += ["", "## Most common roles", ""] + [f"- {names.get(r, r)} ({r}): {n}" for r, n in applied.most_common(120)]
    lines += ["", "## Examples", ""] + [f"- {e}" for e in examples]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
