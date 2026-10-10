"""PubChem PUG REST: element properties, compound properties and 3D conformers."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Iterable, Iterator
from typing import Any

import httpx

from ..http import Fetcher, RetryableError

log = logging.getLogger("p3d.pubchem")

BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PROPERTY_BATCH = 100
SDF_BATCH = 10

# ConformerCount3D tells which CIDs have a 3D record, so SDF requests never miss.
PROPERTIES_PRIMARY = "MolecularFormula,MolecularWeight,SMILES,InChIKey,IUPACName,Charge,ConformerCount3D"
PROPERTIES_FALLBACK = "MolecularFormula,MolecularWeight,IsomericSMILES,InChIKey,IUPACName,Charge,ConformerCount3D"


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
        try:
            body = fetcher.get(f"{BASE}/compound/cid/{ids}/property/{PROPERTIES_PRIMARY}/JSON")
            if body is None:
                body = fetcher.get(f"{BASE}/compound/cid/{ids}/property/{PROPERTIES_FALLBACK}/JSON")
        except (RetryableError, httpx.HTTPError) as error:
            # Skip the batch; it is not cached, so the next run tries again.
            fetcher.stats["failed_batches"] += 1
            log.warning("PubChem properties failed for %d CIDs: %s", len(batch), error)
            continue
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
                "conformers3d": int(item.get("ConformerCount3D", 0) or 0),
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


def conformers_3d(
    fetcher: Fetcher,
    cids: Iterable[int],
    *,
    budget_s: float | None = None,
    max_failures: int = 3,
) -> dict[int, str]:
    """3D SDF records by CID. Batches that come back empty are split in halves.

    PubChem blocks clients that ask too much (HTTP 429 for hours). After `max_failures`
    failed batches in a row, or after `budget_s` seconds, the rest is served from the
    cache only; callers fall back to RDKit, and the next run continues.
    """
    result: dict[int, str] = {}
    started = time.monotonic()
    state = {"failures": 0, "offline": False}

    def fetch(batch: list[int]) -> None:
        ids = ",".join(map(str, batch))
        if not state["offline"] and budget_s is not None and time.monotonic() - started > budget_s:
            log.warning("PubChem 3D: time budget used up, continuing from the cache only")
            state["offline"] = True
        try:
            body = fetcher.get(
                f"{BASE}/compound/cid/{ids}/SDF",
                {"record_type": "3d"},
                cache_only=bool(state["offline"]),
                attempts=4,  # a throttled host stays throttled: give up early, use RDKit
            )
            state["failures"] = 0
        except (RetryableError, httpx.HTTPError) as error:
            fetcher.stats["failed_batches"] += 1
            log.warning("PubChem 3D failed for %d CIDs: %s", len(batch), error)
            state["failures"] = int(state["failures"]) + 1
            if int(state["failures"]) >= max_failures and not state["offline"]:
                log.warning("PubChem 3D: %d failures in a row, continuing from the cache only", max_failures)
                state["offline"] = True
            return
        if body is None:
            if len(batch) > 1 and not state["offline"]:
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

    batches = list(_chunks(sorted(set(cids)), SDF_BATCH))
    for number, batch in enumerate(batches, start=1):
        if number % 200 == 0:
            log.info("  3D batches: %d/%d, %d records, %s", number, len(batches), len(result), dict(fetcher.stats))
        fetch(batch)
    return result
