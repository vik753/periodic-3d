"""Materials Project structures via the public OPTIMADE API (no key needed)."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import httpx

from ..http import Fetcher, RetryableError

log = logging.getLogger("p3d.optimade")

BASE = "https://optimade.materialsproject.org/v1/structures"
FORMULA_BATCH = 25
ID_BATCH = 20
PAGE_LIMIT = 100


@dataclass(frozen=True)
class Candidate:
    id: str
    reduced: str
    nsites: int
    energy_above_hull: float | None


def _energy_above_hull(stability: Any) -> float | None:
    """Smallest energy_above_hull found anywhere in the _mp_stability object."""
    best: float | None = None
    stack = [stability]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "energy_above_hull" and isinstance(value, int | float):
                    best = float(value) if best is None else min(best, float(value))
                else:
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)
    return best


def _paged(fetcher: Fetcher, params: dict[str, str]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    offset = 0
    while True:
        page = {**params, "page_limit": str(PAGE_LIMIT), "page_offset": str(offset)}
        try:
            body = fetcher.get(BASE, page, accept="application/json")
        except (RetryableError, httpx.HTTPError) as error:
            fetcher.stats["failed_batches"] += 1
            log.warning("OPTIMADE query failed: %s", error)
            break
        if body is None:
            break
        data = json.loads(body)
        batch = data.get("data", [])
        entries.extend(batch)
        more = data.get("meta", {}).get("more_data_available", False)
        if not more or not batch:
            break
        offset += len(batch)
    return entries


def candidates(fetcher: Fetcher, reduced_formulas: Iterable[str]) -> dict[str, list[Candidate]]:
    """Structures per reduced formula (alphabetical OPTIMADE notation, e.g. 'ClNa')."""
    unique = sorted(set(reduced_formulas))
    result: dict[str, list[Candidate]] = {}
    for start in range(0, len(unique), FORMULA_BATCH):
        batch = unique[start : start + FORMULA_BATCH]
        flt = " OR ".join(f'chemical_formula_reduced="{formula}"' for formula in batch)
        for entry in _paged(
            fetcher,
            {"filter": flt, "response_fields": "chemical_formula_reduced,nsites,_mp_stability"},
        ):
            attributes = entry.get("attributes", {})
            reduced = attributes.get("chemical_formula_reduced")
            if not reduced:
                continue
            result.setdefault(reduced, []).append(
                Candidate(
                    id=str(entry["id"]),
                    reduced=reduced,
                    nsites=int(attributes.get("nsites") or 0),
                    energy_above_hull=_energy_above_hull(attributes.get("_mp_stability")),
                )
            )
    return result


# Structures within this energy (eV/atom) of the most stable one count as equally good.
STABILITY_WINDOW = 0.02


def _mp_number(identifier: str) -> int:
    digits = identifier.rsplit("-", 1)[-1]
    return int(digits) if digits.isdigit() else 10**9


def best_candidate(options: list[Candidate]) -> Candidate | None:
    """The most stable structure, preferring long-standing Materials Project entries.

    Among structures within STABILITY_WINDOW of the most stable one, the lowest MP id
    wins. Old ids come from known experimental structures (ICSD); recent ids include
    machine-generated candidates such as GNoME (CC BY-NC), which the project excludes
    (ADR 0004). OPTIMADE does not report the origin, so this is the practical guard.
    """
    if not options:
        return None
    energies = [c.energy_above_hull for c in options if c.energy_above_hull is not None]
    floor = min(energies) if energies else None

    def key(c: Candidate) -> tuple[int, int, int, str]:
        energy = c.energy_above_hull
        near = floor is not None and energy is not None and energy <= floor + STABILITY_WINDOW
        return (0 if near else 1, _mp_number(c.id), c.nsites, c.id)

    return min(options, key=key)


def structures(fetcher: Fetcher, ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    """Full structures (lattice, positions, species) by Materials Project id."""
    unique = sorted(set(ids))
    result: dict[str, dict[str, Any]] = {}
    fields = "chemical_formula_reduced,lattice_vectors,cartesian_site_positions,species_at_sites,nsites"
    for start in range(0, len(unique), ID_BATCH):
        batch = unique[start : start + ID_BATCH]
        flt = " OR ".join(f'id="{identifier}"' for identifier in batch)
        for entry in _paged(fetcher, {"filter": flt, "response_fields": fields}):
            result[str(entry["id"])] = entry.get("attributes", {})
    return result
