"""Probe: PubChem use annotations in bulk, by heading (task U.1).

Per-compound PUG-View requests get throttled (HTTP 429) after a few dozen compounds.
The annotations endpoint returns one heading for all compounds, page by page:
  /rest/pug_view/annotations/heading/<heading>/JSON?heading_type=Compound&page=N
For each candidate heading this script reads up to MAX_PAGES pages and reports the total
pages, the sources, how many of our compounds are covered and sample values.

Usage: python3 tools/probe/pubchem_headings.py <cids.txt> <out-dir>
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/annotations/heading/{}/JSON"
HEADINGS = [
    "Use Classification",
    "Uses",
    "Industry Uses",
    "Consumer Uses",
    "Therapeutic Uses",
    "MeSH Pharmacological Classification",
    "Drug Classes",
    "Food Additive Classes",
    "Agrochemical Category",
    "Pesticides",
    "Cosmetics",
]
MAX_PAGES = 40
PAUSE = 1.5


def get(url: str) -> dict | None:
    for attempt in range(4):
        request = urllib.request.Request(url, headers={"User-Agent": "periodic-3d probe (github.com/vik753/periodic-3d)"})
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            print(f"{url}: HTTP {error.code}, attempt {attempt + 1}")
            time.sleep(10 * (attempt + 1))
        except Exception as error:  # a probe reports every failure and goes on
            print(f"{url}: {error}, attempt {attempt + 1}")
            time.sleep(10 * (attempt + 1))
    return None


def strings(data: list[dict]) -> list[str]:
    values = []
    for item in data:
        for value in item.get("Value", {}).get("StringWithMarkup", []) or []:
            values.append(value.get("String", ""))
    return values


def main() -> None:
    ours = {int(line) for line in Path(sys.argv[1]).read_text().split() if line.strip()}
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# Probe: PubChem use annotations by heading", "", f"Our compounds with a CID: {len(ours)}", ""]
    summary = {}
    for heading in HEADINGS:
        url = BASE.format(urllib.parse.quote(heading)) + "?heading_type=Compound&page={}"
        first = get(url.format(1))
        time.sleep(PAUSE)
        if not first:
            lines += [f"## {heading}", "", "no data", ""]
            continue
        total = int(first.get("Annotations", {}).get("TotalPages", 1))
        sources: Counter[str] = Counter()
        covered: set[int] = set()
        by_source: dict[str, set[int]] = {}
        samples: dict[str, list[str]] = {}
        annotations = 0
        pages = min(total, MAX_PAGES)
        for page in range(1, pages + 1):
            body = first if page == 1 else get(url.format(page))
            if page > 1:
                time.sleep(PAUSE)
            if not body:
                continue
            for annotation in body.get("Annotations", {}).get("Annotation", []):
                annotations += 1
                source = annotation.get("SourceName", "?")
                sources[source] += 1
                cids = set(annotation.get("LinkedRecords", {}).get("CID", []) or [])
                hit = cids & ours
                covered |= hit
                by_source.setdefault(source, set()).update(hit)
                if hit and len(samples.setdefault(source, [])) < 6:
                    text = " | ".join(strings(annotation.get("Data", [])))[:240]
                    samples[source].append(f"{annotation.get('Name', '')}: {text}")
        summary[heading] = {"pages": total, "read": pages, "annotations": annotations, "covered": len(covered)}
        lines += [
            f"## {heading}",
            "",
            f"Total pages: {total}; read: {pages}; annotations read: {annotations}; our compounds covered in"
            f" the read pages: {len(covered)}",
            "",
            "| Source | Annotations | Our compounds |",
            "| --- | --- | --- |",
        ]
        lines += [f"| {name} | {count} | {len(by_source.get(name, set()))} |" for name, count in sources.most_common(25)]
        lines.append("")
        for name, values in samples.items():
            lines += [f"- **{name}**"] + [f"  - {value}" for value in values]
        lines.append("")
        print(heading, summary[heading], flush=True)
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
