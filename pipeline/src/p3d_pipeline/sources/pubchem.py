"""PubChem PUG REST: element properties, compound properties and 3D conformers."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from typing import Any

from ..http import Fetcher

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PROPERTY_BATCH = 100
SDF_BATCH = 10

PROPERTIES_PRIMARY = "MolecularFormula,MolecularWeight,SMILES,InChIKey,IUPACName,Charge"
PROPERTIES_FALLBACK = "MolecularFormula,MolecularWeight,IsomericSMILES,InChIKey,IUPACName,Charge"


def _chunks(values: list[int], size: int) -> Iterator[list[int]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def periodic_table(fetcher: Fetcher) -> dict[int, dict[str, str]]:
    """PubChem periodic table: one dict of string cells per atomic number."""
    body = fetcher.get(f"{BASE}/periodictable/JSON")
    if body is None:
        raise RuntimeError("PubChem periodic table is not available")
    table = json.loads(body)["Table"]
    columns: list[str] = table["Columns"]["Column"]
    result: dict[int, dict[str, str]] = {}
    for row in table["Row"]:
        cells = dict(zip(columns, row["Cell"], strict=False))
        result[int(cells["AtomicNumber"])] = cells
    return result


def properties(fetcher: Fetcher, cids: Iterable[int]) -> dict[int, dict[str, Any]]:
    """Compound properties by CID, fetched in batches."""
    result: dict[int, dict[str, Any]] = {}
    for batch in _chunks(sorted(set(cids)), PROPERTY_BATCH):
        ids = ",".join(map(str, batch))
        body = fetcher.get(f"{BASE}/compound/cid/{ids}/property/{PROPERTIES_PRIMARY}/JSON")
        if body is None:
            body = fetcher.get(f"{BASE}/compound/cid/{ids}/property/{PROPERTIES_FALLBACK}/JSON")
        if body is None:
            continue
        for item in json.loads(body).get("PropertyTable", {}).get("Properties", []):
            cid = int(item["CID"])
            smiles = item.get("SMILES") or item.get("IsomericSMILES") or item.get("CanonicalSMILES")
            result[cid] = {
                "formula": item.get("MolecularFormula"),
                "mass": float(item["MolecularWeight"]) if item.get("MolecularWeight") else None,
                "smiles": smiles,
                "inchikey": item.get("InChIKey"),
                "iupac": item.get("IUPACName"),
                "charge": int(item.get("Charge", 0) or 0),
            }
    return result


def split_sdf(text: str) -> Iterator[str]:
    for record in text.split("$$$$"):
        if record.strip():
            yield record.strip("\n") + "\n"


def _sdf_cid(record: str) -> int | None:
    lines = record.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("> ") and "<PUBCHEM_COMPOUND_CID>" in line and index + 1 < len(lines):
            value = lines[index + 1].strip()
            return int(value) if value.isdigit() else None
    return None


def conformers_3d(fetcher: Fetcher, cids: Iterable[int]) -> dict[int, str]:
    """3D SDF records by CID. Batches that fail are split in halves until each CID is tried."""
    result: dict[int, str] = {}

    def fetch(batch: list[int]) -> None:
        ids = ",".join(map(str, batch))
        body = fetcher.get(f"{BASE}/compound/cid/{ids}/SDF", {"record_type": "3d"})
        if body is None:
            if len(batch) > 1:
                middle = len(batch) // 2
                fetch(batch[:middle])
                fetch(batch[middle:])
            return
        for record in split_sdf(body.decode("utf-8", errors="replace")):
            cid = _sdf_cid(record)
            if cid is None and len(batch) == 1:
                cid = batch[0]
            if cid is not None:
                result[cid] = record

    for batch in _chunks(sorted(set(cids)), SDF_BATCH):
        fetch(batch)
    return result
