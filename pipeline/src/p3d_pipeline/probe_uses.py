"""Probe: where can "uses" of elements and compounds come from, and how much do we get?

Measures, for the dataset selection (ADR 0004) and a sample of the most famous compounds:

- Wikidata P366 "has use": how many items have it, the most common uses with labels in
  three languages, their classes (P31/P279) for a mapping to ten spheres, and how many
  statements carry a reference;
- PubChem PUG-View: which "use" headings exist (Use and Manufacturing, drug, agrochemical,
  food additive information) and which sources stand behind them.

Writes report.md and JSON samples. Used once to design the uses layer (task U.1).
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

from .http import Fetcher
from .sources import wikidata
from .sources.wikidata import LANGUAGES, qid, sparql

log = logging.getLogger("p3d.probe_uses")

SELECTION = """?item wdt:P274 ?formula .
  ?article schema:about ?item ; schema:isPartOf ?wiki .
  VALUES ?wiki { <https://en.wikipedia.org/> <https://ru.wikipedia.org/> <https://uk.wikipedia.org/> }"""

EXTRA_PREFIXES = """PREFIX p: <http://www.wikidata.org/prop/>
PREFIX ps: <http://www.wikidata.org/prop/statement/>
PREFIX prov: <http://www.w3.org/ns/prov#>
"""

PUG_VIEW = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON"
HEADINGS = (
    "Use and Manufacturing",
    "Drug and Medication Information",
    "Agrochemical Information",
    "Food Additives and Ingredients",
    "Pharmacology and Biochemistry",
)
# The most famous compounds of the sample show their raw use data in the report.
SHOWCASE_SIZE = 14


def _wikidata(fetcher: Fetcher, elements: list[dict[str, Any]], showcase_ids: set[str]) -> dict[str, Any]:
    counts = sparql(
        fetcher,
        f"""SELECT (COUNT(DISTINCT ?item) AS ?items) WHERE {{ {SELECTION} }}""",
    )
    with_use = sparql(
        fetcher,
        f"""SELECT (COUNT(DISTINCT ?item) AS ?items) (COUNT(?use) AS ?pairs) WHERE {{
          {SELECTION}
          ?item wdt:P366 ?use .
        }}""",
    )
    referenced = sparql(
        fetcher,
        EXTRA_PREFIXES
        + f"""SELECT (COUNT(?statement) AS ?statements) (COUNT(?ref) AS ?referenced) WHERE {{
          {SELECTION}
          ?item p:P366 ?statement .
          OPTIONAL {{ ?statement prov:wasDerivedFrom ?ref . }}
        }}""",
    )
    top = sparql(
        fetcher,
        f"""SELECT ?use (COUNT(DISTINCT ?item) AS ?n) WHERE {{
          {SELECTION}
          ?item wdt:P366 ?use .
        }} GROUP BY ?use ORDER BY DESC(?n) LIMIT 500""",
    )
    element_values = " ".join(f"wd:{e['qid']}" for e in elements)
    element_uses = sparql(
        fetcher,
        f"""SELECT ?item ?use WHERE {{
          VALUES ?item {{ {element_values} }}
          ?item wdt:P366 ?use .
        }}""",
    )
    use_ids = {qid(row["use"]) for row in top} | {qid(row["use"]) for row in element_uses}
    labels = wikidata.fetch_labels(fetcher, use_ids, LANGUAGES)
    classes: dict[str, list[str]] = {}
    ordered = sorted(use_ids)
    for start in range(0, len(ordered), 300):
        values = " ".join(f"wd:{item}" for item in ordered[start : start + 300])
        for row in sparql(
            fetcher,
            f"""SELECT ?use ?class WHERE {{
              VALUES ?use {{ {values} }}
              ?use wdt:P31|wdt:P279 ?class .
            }}""",
        ):
            classes.setdefault(qid(row["use"]), []).append(qid(row["class"]))
    class_labels = wikidata.fetch_labels(fetcher, {c for values in classes.values() for c in values}, ("en",))
    showcase = sparql(
        fetcher,
        f"""SELECT ?item ?use WHERE {{
          VALUES ?item {{ {" ".join(f"wd:{item}" for item in sorted(showcase_ids))} }}
          ?item wdt:P366 ?use .
        }}""",
    )
    return {
        "selection": int(counts[0]["items"]),
        "with_use": int(with_use[0]["items"]),
        "pairs": int(with_use[0]["pairs"]),
        "statements": int(referenced[0]["statements"]),
        "referenced": int(referenced[0]["referenced"]),
        "top": [
            {
                "use": qid(row["use"]),
                "items": int(row["n"]),
                "labels": labels.get(qid(row["use"]), {}),
                "classes": [
                    {"id": c, "label": class_labels.get(c, {}).get("en", "")} for c in classes.get(qid(row["use"]), [])
                ],
            }
            for row in top
        ],
        "elements": sorted(
            {(qid(row["item"]), qid(row["use"]), labels.get(qid(row["use"]), {}).get("en", "")) for row in element_uses}
        ),
        "element_items": len({qid(row["item"]) for row in element_uses}),
        "showcase": sorted(
            {(qid(row["item"]), labels.get(qid(row["use"]), {}).get("en", qid(row["use"]))) for row in showcase}
        ),
    }


def _walk(section: dict[str, Any], path: list[str], found: list[tuple[str, int]]) -> None:
    heading = section.get("TOCHeading", "")
    here = [*path, heading] if heading else path
    information = section.get("Information") or []
    if information:
        found.append((" / ".join(here), len(information)))
    for child in section.get("Section") or []:
        _walk(child, here, found)


def _pubchem(fetcher: Fetcher, compounds: list[dict[str, Any]], showcase_ids: set[str]) -> dict[str, Any]:
    headings: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    covered: Counter[str] = Counter()
    failures: Counter[str] = Counter()
    samples: dict[str, Any] = {}
    for number, compound in enumerate(compounds, start=1):
        if number % 50 == 0:
            log.info("PubChem: %d/%d", number, len(compounds))
        for heading in HEADINGS:
            try:
                body = fetcher.get(PUG_VIEW.format(cid=compound["cid"]), {"heading": heading}, attempts=6)
            except Exception as error:  # a throttled request must not stop the probe
                log.warning("PubChem %s %s: %s", compound["cid"], heading, error)
                failures[heading] += 1
                continue
            if body is None:
                continue
            data = json.loads(body).get("Record", {})
            found: list[tuple[str, int]] = []
            for section in data.get("Section") or []:
                _walk(section, [], found)
            if found:
                covered[heading] += 1
            for path, _count in found:
                headings[path] += 1
            for reference in data.get("Reference") or []:
                sources[reference.get("SourceName", "?")] += 1
            if compound["qid"] in showcase_ids:
                samples.setdefault(compound["name"], {})[heading] = _texts(data)[:12]
    return {
        "sample": len(compounds),
        "covered": dict(covered),
        "failures": dict(failures),
        "headings": headings.most_common(80),
        "sources": sources.most_common(60),
        "samples": samples,
    }


def _texts(record: dict[str, Any]) -> list[str]:
    texts: list[str] = []

    def visit(section: dict[str, Any], path: str) -> None:
        heading = section.get("TOCHeading", "")
        here = f"{path} / {heading}" if path else heading
        for information in section.get("Information") or []:
            value = information.get("Value", {})
            strings = [s.get("String", "") for s in value.get("StringWithMarkup") or []]
            if strings:
                texts.append(f"[{here}] " + " | ".join(strings)[:300])
        for child in section.get("Section") or []:
            visit(child, here)

    for section in record.get("Section") or []:
        visit(section, "")
    return texts


def run_probe(sample_path: Path, cache: Path, out: Path) -> Path:
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    # PUG-View throttles harder than PUG-REST: one request per second.
    fetcher = Fetcher(cache, rates={"pubchem.ncbi.nlm.nih.gov": 1.0})
    out.mkdir(parents=True, exist_ok=True)
    showcase_ids = {compound["qid"] for compound in sample["compounds"][:SHOWCASE_SIZE]}
    wd = _wikidata(fetcher, sample["elements"], showcase_ids)
    (out / "wikidata.json").write_text(json.dumps(wd, ensure_ascii=False, indent=1), encoding="utf-8")
    pc = _pubchem(fetcher, sample["compounds"], showcase_ids)
    (out / "pubchem.json").write_text(json.dumps(pc, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# Probe: uses of elements and compounds", ""]
    lines += [
        "## Wikidata P366 (has use)",
        "",
        f"- Selection (formula + article): {wd['selection']} items",
        f"- With P366: {wd['with_use']} items, {wd['pairs']} item–use pairs",
        f"- P366 statements with a reference: {wd['referenced']} of {wd['statements']}",
        f"- Elements with P366: {wd['element_items']} of {len(sample['elements'])}",
        "",
        "### Most common uses",
        "",
        "| Use | Items | en | uk | ru | Classes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in wd["top"][:150]:
        names = row["labels"]
        classes = ", ".join(f"{c['label'] or c['id']} ({c['id']})" for c in row["classes"][:4])
        lines.append(
            f"| {row['use']} | {row['items']} | {names.get('en', '')} | {names.get('uk', '')} | "
            f"{names.get('ru', '')} | {classes} |"
        )
    lines += ["", "### Showcase", ""] + [f"- {item}: {use}" for item, use in wd["showcase"]]
    lines += ["", "### Elements", ""] + [f"- {item}: {label or use}" for item, use, label in wd["elements"][:200]]
    lines += [
        "",
        "## PubChem PUG-View",
        "",
        f"Sample: the {pc['sample']} most famous compounds with a CID.",
        "",
        "| Heading | Compounds with data |",
        "| --- | --- |",
    ]
    lines += [f"| {heading} | {count} |" for heading, count in sorted(pc["covered"].items())]
    lines += ["", f"Failed requests: {pc['failures']}"]
    lines += ["", "### Subsections", ""] + [f"- {path}: {count}" for path, count in pc["headings"]]
    lines += ["", "### Sources", ""] + [f"- {name}: {count}" for name, count in pc["sources"]]
    for name, sections in pc["samples"].items():
        lines += ["", f"### {name}", ""]
        for heading, texts in sections.items():
            lines += [f"- **{heading}**"] + [f"  - {text}" for text in texts]
    report = out / "report.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
