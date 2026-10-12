"""Probe: USGS Mineral Commodity Summaries — end uses of mineral commodities (task U.1).

Downloads a few commodity sheets (PDF, public domain), extracts the "Domestic Production
and Use" paragraph and the shares of end uses ("…batteries, 87%…"). Writes report.md.

Usage: python3 tools/probe/usgs.py <out-dir>
"""

from __future__ import annotations

import io
import re
import sys
import urllib.request
from pathlib import Path

from pypdf import PdfReader

COMMODITIES = ["lithium", "copper", "aluminum", "cobalt", "rare-earths", "gold", "silver", "titanium", "nickel", "zinc", "helium", "iodine"]
YEARS = ["2026", "2025"]
SHARE = re.compile(r"([a-z][a-z ,\-()]{3,80}?),?\s+(\d{1,2}(?:\.\d)?)%")


def fetch(url: str) -> bytes | None:
    request = urllib.request.Request(url, headers={"User-Agent": "periodic-3d probe (github.com/vik753/periodic-3d)"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except Exception as error:  # noqa: BLE001 - a probe reports every failure
        print(f"{url}: {error}")
        return None


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# Probe: USGS Mineral Commodity Summaries", ""]
    for name in COMMODITIES:
        for year in YEARS:
            url = f"https://pubs.usgs.gov/periodicals/mcs{year}/mcs{year}-{name}.pdf"
            data = fetch(url)
            if not data:
                continue
            text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)
            text = re.sub(r"\s+", " ", text)
            match = re.search(r"Domestic Production and Use:(.*?)(Salient Statistics|Recycling:)", text)
            paragraph = match.group(1).strip() if match else "(paragraph not found)"
            shares = SHARE.findall(paragraph)
            lines += [f"## {name} ({year})", "", url, "", paragraph[:1500], "", "Shares:"]
            lines += [f"- {use.strip()}: {value}%" for use, value in shares] or ["- none"]
            lines.append("")
            break
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
