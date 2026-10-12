"""Probe: USGS Mineral Commodity Summaries — end uses of mineral commodities (task U.5).

Downloads the commodity sheets (PDF, U.S. Government work, public domain), extracts the
"Domestic Production and Use" paragraph and writes them to paragraphs.json and report.md.
The agent reads the paragraphs and curates the end-use shares by hand into
pipeline/data/usgs_end_uses.json: automatic share parsing picks up prices and State
shares, so the numbers are typed and checked against the quoted text.

Usage: python3 tools/probe/usgs.py <out-dir>
"""

from __future__ import annotations

import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

from pypdf import PdfReader

# Commodity sheet names (the file name after "mcs<year>-"). Several spellings are tried.
COMMODITIES = {
    "aluminum": ["aluminum"],
    "antimony": ["antimony"],
    "arsenic": ["arsenic"],
    "barite": ["barite"],
    "beryllium": ["beryllium"],
    "bismuth": ["bismuth"],
    "boron": ["boron"],
    "bromine": ["bromine"],
    "cadmium": ["cadmium"],
    "cesium": ["cesium"],
    "chromium": ["chromium"],
    "cobalt": ["cobalt"],
    "copper": ["copper"],
    "diamond": ["diamond-industrial", "diamond"],
    "fluorspar": ["fluorspar"],
    "gallium": ["gallium"],
    "germanium": ["germanium"],
    "gold": ["gold"],
    "graphite": ["graphite"],
    "hafnium": ["hafnium", "zirconium-hafnium"],
    "helium": ["helium"],
    "indium": ["indium"],
    "iodine": ["iodine"],
    "iron-ore": ["iron-ore"],
    "iron-steel": ["iron-steel"],
    "lead": ["lead"],
    "lithium": ["lithium"],
    "magnesium-metal": ["magnesium-metal", "magnesium"],
    "magnesium-compounds": ["magnesium-compounds"],
    "manganese": ["manganese"],
    "mercury": ["mercury"],
    "molybdenum": ["molybdenum"],
    "nickel": ["nickel"],
    "niobium": ["niobium"],
    "nitrogen": ["nitrogen"],
    "phosphate": ["phosphate-rock", "phosphate"],
    "platinum": ["platinum", "platinum-group-metals"],
    "potash": ["potash"],
    "rare-earths": ["rare-earths"],
    "rhenium": ["rhenium"],
    "rubidium": ["rubidium"],
    "salt": ["salt"],
    "scandium": ["scandium"],
    "selenium": ["selenium"],
    "silicon": ["silicon"],
    "silver": ["silver"],
    "soda-ash": ["soda-ash"],
    "strontium": ["strontium"],
    "sulfur": ["sulfur"],
    "tantalum": ["tantalum"],
    "tellurium": ["tellurium"],
    "thallium": ["thallium"],
    "thorium": ["thorium"],
    "tin": ["tin"],
    "titanium": ["titanium"],
    "tungsten": ["tungsten"],
    "vanadium": ["vanadium"],
    "yttrium": ["yttrium"],
    "zinc": ["zinc"],
    "zirconium": ["zirconium-hafnium", "zirconium"],
}
YEARS = ["2026", "2025"]
PARAGRAPH = re.compile(r"Domestic Production and Use:(.*?)(Salient Statistics|Recycling:|Import Sources)", re.S)


def fetch(url: str) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": "periodic-3d probe (github.com/vik753/periodic-3d)"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            print(f"{url}: HTTP {error.code}")
        except Exception as error:  # noqa: BLE001 - a probe reports every failure
            print(f"{url}: {error}")
        time.sleep(5 * (attempt + 1))
    return None


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# Probe: USGS Mineral Commodity Summaries — Domestic Production and Use", ""]
    found: dict[str, dict[str, str]] = {}
    for commodity, names in COMMODITIES.items():
        hit = None
        for year in YEARS:
            for name in names:
                url = f"https://pubs.usgs.gov/periodicals/mcs{year}/mcs{year}-{name}.pdf"
                data = fetch(url)
                time.sleep(1)
                if data:
                    hit = (year, url, data)
                    break
            if hit:
                break
        if not hit:
            lines += [f"## {commodity}", "", "not found", ""]
            print(commodity, "not found", flush=True)
            continue
        year, url, data = hit
        text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
        text = re.sub(r"\s+", " ", text)
        match = PARAGRAPH.search(text)
        paragraph = match.group(1).strip() if match else ""
        found[commodity] = {"year": year, "url": url, "paragraph": paragraph}
        lines += [f"## {commodity} ({year})", "", url, "", paragraph or "(paragraph not found)", ""]
        print(commodity, year, len(paragraph), flush=True)
    (out / "paragraphs.json").write_text(json.dumps(found, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
