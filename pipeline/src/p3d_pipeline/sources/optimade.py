"""Materials Project structures via the public OPTIMADE API (no key needed)."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..http import Fetcher

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
        body = fetcher.get(BASE, page, accept="application/json")
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


def best_candidate(options: list[Candidate]) -> Candidate | None:
    """Most stable structure; ties go to the smaller cell."""
    if not options:
        return None
    return min(
        options,
        key=lambda c: (c.energy_above_hull if c.energy_above_hull is not None else 9.9, c.nsites, c.id),
    )


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
