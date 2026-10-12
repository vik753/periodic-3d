"""Probe: what PubChem element pages say about uses (task U.1).

PubChem element records (https://pubchem.ncbi.nlm.nih.gov/element/<Z>) collect texts
from Los Alamos National Laboratory, Jefferson Lab, USGS and others. This script reads
the record of each element and reports the sections, the sources and the "Uses" texts.

Usage: python3 tools/probe/pubchem_elements.py <out-dir>
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/element/{}/JSON"


def fetch(url: str) -> dict | None:
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "periodic-3d probe (github.com/vik753/periodic-3d)"})
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read())
        except Exception as error:  # report and retry
            print(f"{url}: {error}")
            time.sleep(15 * (attempt + 1))
    return None


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    sections: Counter[str] = Counter()
    sources: Counter[str] = Counter()
    lines = ["# Probe: PubChem element pages", ""]
    uses: dict[int, list[str]] = {}
    for z in range(1, 119):
        record = fetch(URL.format(z))
        time.sleep(2.5)
        if not record:
            continue
        record = record.get("Record", {})
        refs = {ref.get("ReferenceNumber"): ref.get("SourceName", "?") for ref in record.get("Reference", [])}

        def walk(section: dict, path: str) -> None:
            heading = section.get("TOCHeading", "")
            here = f"{path} / {heading}" if path else heading
            for info in section.get("Information", []) or []:
                sections[here] += 1
                source = refs.get(info.get("ReferenceNumber"), "?")
                sources[source] += 1
                if "use" in here.lower() or "application" in here.lower():
                    text = " ".join(v.get("String", "") for v in info.get("Value", {}).get("StringWithMarkup", []) or [])
                    uses.setdefault(z, []).append(f"[{here} — {source}] {text[:400]}")
            for child in section.get("Section", []) or []:
                walk(child, here)

        for section in record.get("Section", []) or []:
            walk(section, "")
    lines += ["## Sections", ""] + [f"- {name}: {n}" for name, n in sections.most_common(60)]
    lines += ["", "## Sources", ""] + [f"- {name}: {n}" for name, n in sources.most_common(40)]
    lines += ["", f"## Uses texts ({len(uses)} elements)", ""]
    for z in sorted(uses):
        lines += [f"### Z={z}"] + [f"- {text}" for text in uses[z][:4]]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:60]))


if __name__ == "__main__":
    main()
