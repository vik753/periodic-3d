"""Materials Project API: which crystal structures come from experiment (Q.2).

OPTIMADE does not say where a Materials Project structure comes from. The MP API does:
`theoretical` is false when the structure matches an experimental record (ICSD), and
`database_IDs.icsd` lists those records. The API needs a free key: the environment
variable MP_API_KEY (a GitHub secret in CI). Without it the build goes on without the
marks. The key travels only in a request header: never in a URL, the cache or a log.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from dataclasses import dataclass

import httpx

from ..http import Fetcher, RetryableError

log = logging.getLogger("p3d.mp_api")

BASE = "https://api.materialsproject.org/materials/summary/"
FIELDS = "material_id,theoretical,database_IDs"
ID_BATCH = 100


@dataclass(frozen=True)
class Origin:
    """Where an MP structure comes from: experiment (ICSD records) or calculation only."""

    theoretical: bool
    icsd: tuple[str, ...] = ()

    @property
    def experimental(self) -> bool:
        return not self.theoretical


def legacy_id(identifier: str) -> str:
    """The numeric form of a Materials Project id: "mp-aaaaaaco" → "mp-66".

    The MP API answers with the new alphabetical ids (base 26, a = 0, padded with a);
    OPTIMADE and Wikidata use the numeric ones. A numeric id stays as it is.
    """
    prefix, _, suffix = identifier.rpartition("-")
    if not prefix or not suffix.isascii() or not suffix.isalpha() or not suffix.islower():
        return identifier
    number = 0
    for letter in suffix:
        number = number * 26 + (ord(letter) - ord("a"))
    return f"{prefix}-{number}"


def api_key() -> str | None:
    return os.environ.get("MP_API_KEY", "").strip() or None


def origins(fetcher: Fetcher, ids: Iterable[str]) -> dict[str, Origin]:
    """Origin of each Materials Project id; empty without a key or when the API fails."""
    key = api_key()
    if key is None:
        log.warning("MP_API_KEY is not set: crystals get no experimental or computed mark")
        return {}
    unique = sorted({identifier for identifier in ids if identifier.startswith(("mp-", "mvc-"))})
    result: dict[str, Origin] = {}
    for start in range(0, len(unique), ID_BATCH):
        batch = unique[start : start + ID_BATCH]
        params = {"material_ids": ",".join(batch), "_fields": FIELDS, "_limit": str(len(batch))}
        try:
            body = fetcher.get(BASE, params, accept="application/json", headers={"X-API-KEY": key}, attempts=4)
        except (RetryableError, httpx.HTTPError) as error:
            fetcher.stats["failed_batches"] += 1
            # The error names the URL and the status only; the key is in a header.
            log.warning("MP API batch failed: %s", error)
            continue
        if body is None:
            continue
        for document in json.loads(body).get("data", []):
            identifier = document.get("material_id")
            if not identifier:
                continue
            database_ids = document.get("database_IDs") or {}
            icsd = tuple(str(value) for value in database_ids.get("icsd", []) or [])
            result[legacy_id(str(identifier))] = Origin(theoretical=bool(document.get("theoretical", True)), icsd=icsd)
    log.info("MP API: origin of %d of %d structures", len(result), len(unique))
    return result
