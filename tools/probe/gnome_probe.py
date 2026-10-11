"""Measure the GNoME dataset before building on it (sizes, counts, structure encoding).

Usage: python tools/probe/gnome_probe.py <out-dir>
Writes <out-dir>/report.json, <out-dir>/report.md and a few sample CIF files.
Standard library only: runs in a bare CI job.
"""

from __future__ import annotations

import collections
import csv
import gzip
import io
import json
import math
import re
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

BASE = "https://storage.googleapis.com/gdm_materials_discovery"
FILES = [
    "gnome_data/stable_materials_summary.csv",
    "gnome_data/stable_materials_r2scan.csv",
    "gnome_data/by_id.zip",
    "gnome_data/by_composition.zip",
    "gnome_data/by_reduced_formula.zip",
    "external_data/external_materials_summary.csv",
    "external_data/mp_snapshot_summary.csv",
]
UA = "periodic-3d/0.1 (https://github.com/vik753/periodic-3d; data probe)"


def head(url: str) -> dict[str, str]:
    request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return {"status": str(response.status), "bytes": response.headers.get("Content-Length", "?")}
    except Exception as error:  # noqa: BLE001 - a probe reports every failure
        return {"status": "error", "error": str(error)}


def download(url: str, target: Path) -> float:
    started = time.monotonic()
    request = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(request, timeout=600) as response, target.open("wb") as out:
        while chunk := response.read(1 << 20):
            out.write(chunk)
    return time.monotonic() - started


_NUMBER = re.compile(r"^[-+0-9.eE]+")


def number(text: str) -> float:
    match = _NUMBER.match(text)
    return float(match.group(0)) if match else math.nan


def parse_cif(text: str) -> dict[str, object]:
    """Cell and sites from a P1 CIF (pymatgen style). Enough to measure the encoding."""
    values: dict[str, str] = {}
    sites: list[list[object]] = []
    lines = [line.strip() for line in text.splitlines()]
    index = 0
    symops = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith("_") and not line.startswith("_atom_site") and " " in line:
            key, value = line.split(None, 1)
            values[key] = value.strip("'\"")
        if line == "loop_":
            keys: list[str] = []
            index += 1
            while index < len(lines) and lines[index].startswith("_"):
                keys.append(lines[index].split()[0])
                index += 1
            rows: list[list[str]] = []
            while index < len(lines) and lines[index] and not lines[index].startswith(("_", "loop_", "data_")):
                rows.append(lines[index].split())
                index += 1
            if "_symmetry_equiv_pos_as_xyz" in keys or "_space_group_symop_operation_xyz" in keys:
                symops = len(rows)
            if "_atom_site_fract_x" in keys:
                k = {name: position for position, name in enumerate(keys)}
                for row in rows:
                    if len(row) < len(keys):
                        continue
                    symbol = row[k.get("_atom_site_type_symbol", 0)]
                    symbol = re.match(r"[A-Z][a-z]?", symbol).group(0) if re.match(r"[A-Z][a-z]?", symbol) else symbol
                    occupancy = number(row[k["_atom_site_occupancy"]]) if "_atom_site_occupancy" in k else 1.0
                    sites.append(
                        [symbol]
                        + [number(row[k[f"_atom_site_fract_{axis}"]]) for axis in "xyz"]
                        + [occupancy]
                    )
            continue
        index += 1
    cell = [number(values.get(f"_cell_{name}", "nan")) for name in
            ("length_a", "length_b", "length_c", "angle_alpha", "angle_beta", "angle_gamma")]
    return {"cell": cell, "sites": sites, "symops": symops, "spacegroup": values.get("_symmetry_space_group_name_H-M")}


def compact(parsed: dict[str, object]) -> str:
    """Candidate encoding for the site: cell parameters and sites rounded to 4 decimals."""
    sites = parsed["sites"]
    data = {
        "c": [round(v, 4) for v in parsed["cell"]],  # type: ignore[union-attr]
        "s": [[s[0], round(s[1], 4), round(s[2], 4), round(s[3], 4)] for s in sites],  # type: ignore[union-attr,index]
    }
    return json.dumps(data, separators=(",", ":"))


def percentile(values: list[float], share: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))] if ordered else math.nan


def main() -> None:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    work = Path("gnome-probe-data")
    work.mkdir(exist_ok=True)
    report: dict[str, object] = {"heads": {name: head(f"{BASE}/{name}") for name in FILES}}

    summary_path = work / "summary.csv"
    report["summary_download_s"] = round(download(f"{BASE}/gnome_data/stable_materials_summary.csv", summary_path), 1)
    with summary_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        report["summary_columns"] = reader.fieldnames
    report["summary_rows"] = len(rows)
    report["summary_sample"] = rows[:3]
    nsites = [float(row.get("NSites") or 0) for row in rows]
    report["nsites"] = {
        "p50": percentile(nsites, 0.5), "p90": percentile(nsites, 0.9), "p99": percentile(nsites, 0.99),
        "max": max(nsites) if nsites else None, "sum": sum(nsites),
    }
    element_count: collections.Counter[str] = collections.Counter()
    arity: collections.Counter[int] = collections.Counter()
    pairs: collections.Counter[tuple[str, str]] = collections.Counter()
    for row in rows:
        elements = re.findall(r"[A-Z][a-z]?", row.get("Elements") or row.get("Reduced Formula") or "")
        unique = sorted(set(elements))
        arity[len(unique)] += 1
        element_count.update(unique)
        for i, a in enumerate(unique):
            for b in unique[i + 1 :]:
                pairs[(a, b)] += 1
    report["elements"] = dict(element_count.most_common())
    report["arity"] = dict(sorted(arity.items()))
    report["pairs"] = len(pairs)
    report["top_pairs"] = [[f"{a}-{b}", n] for (a, b), n in pairs.most_common(20)]
    for key in ("Crystal System", "Dimensionality Cheon"):
        report[f"by_{key}"] = dict(collections.Counter(row.get(key) for row in rows).most_common(10))
    bandgaps = [float(row["Bandgap"]) for row in rows if row.get("Bandgap") not in (None, "", "nan")]
    report["bandgap_known"] = len(bandgaps)

    zip_path = work / "by_id.zip"
    try:
        report["by_id_download_s"] = round(download(f"{BASE}/gnome_data/by_id.zip", zip_path), 1)
        report["by_id_bytes"] = zip_path.stat().st_size
        with zipfile.ZipFile(zip_path) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            report["by_id_files"] = len(names)
            report["by_id_names_sample"] = names[:5]
            report["by_id_uncompressed"] = sum(info.file_size for info in archive.infolist())
            nested = [name for name in names if name.endswith((".zip", ".tar", ".gz"))]
            report["by_id_nested_archives"] = nested[:5]
            sizes_raw, sizes_compact, sizes_gzip, symops, failures = [], [], [], [], 0
            step = max(1, len(names) // 4000)
            for position, name in enumerate(names[::step]):
                text = archive.read(name).decode("utf-8", "replace")
                if position < 3:
                    (out / Path(name).name).write_text(text, encoding="utf-8")
                try:
                    parsed = parse_cif(text)
                    encoded = compact(parsed)
                    sizes_raw.append(len(text))
                    sizes_compact.append(len(encoded))
                    sizes_gzip.append(len(gzip.compress(encoded.encode(), 6)))
                    symops.append(parsed["symops"])
                except Exception:  # noqa: BLE001
                    failures += 1
            report["cif_sample"] = {
                "parsed": len(sizes_compact), "failures": failures,
                "raw_mean": round(sum(sizes_raw) / max(1, len(sizes_raw))),
                "compact_mean": round(sum(sizes_compact) / max(1, len(sizes_compact))),
                "compact_p95": percentile(sizes_compact, 0.95),
                "gzip_mean": round(sum(sizes_gzip) / max(1, len(sizes_gzip))),
                "symops": dict(collections.Counter(symops).most_common(5)),
            }
            total = len(rows) * report["cif_sample"]["compact_mean"]  # type: ignore[index]
            report["estimated_compact_total_mb"] = round(total / 1e6, 1)
    except Exception as error:  # noqa: BLE001
        report["by_id_error"] = str(error)

    (out / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    lines = ["# GNoME probe", ""]
    for key in ("summary_rows", "pairs", "arity", "nsites", "by_id_bytes", "by_id_files", "by_id_uncompressed",
                "cif_sample", "estimated_compact_total_mb", "heads"):
        lines.append(f"- {key}: {json.dumps(report.get(key), ensure_ascii=False, default=str)}")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
