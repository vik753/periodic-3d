"""Load a pipeline dataset (data/build/<version>/) into PostgreSQL.

The load replaces the previous dataset in one transaction. DELETE (not TRUNCATE)
keeps the old rows visible to running queries until the commit, so the API keeps
answering during a reload.
"""

from __future__ import annotations

import json
import tarfile
import tempfile
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import delete, insert, text
from sqlalchemy.ext.asyncio import AsyncEngine

from .models import EMBEDDING_DIM, ClassRow, CompoundRow, DatasetRow, ElementRow, PairRow
from .text import search_text

SUPPORTED_SCHEMAS = {1}
BATCH = 500


class DatasetError(ValueError):
    """The directory is not a dataset this API understands."""


@dataclass
class LoadReport:
    version: str
    elements: int
    compounds: int
    structures: int
    pairs: int
    classes: int


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def find_dataset(path: Path) -> Path:
    """Accept the dataset directory itself or a parent with exactly one dataset inside."""
    if (path / "manifest.json").is_file():
        return path
    candidates = (
        sorted(child for child in path.iterdir() if (child / "manifest.json").is_file()) if path.is_dir() else []
    )
    if len(candidates) == 1:
        return candidates[0]
    raise DatasetError(f"no single dataset (manifest.json) found in {path}")


@contextmanager
def open_dataset(path: Path) -> Iterator[Path]:
    """Yield a dataset directory from a directory or a .tar.gz archive."""
    if path.is_file() and path.name.endswith((".tar.gz", ".tgz")):
        with tempfile.TemporaryDirectory(prefix="p3d-dataset-") as tmp:
            with tarfile.open(path, "r:gz") as archive:
                archive.extractall(tmp, filter="data")
            yield find_dataset(Path(tmp))
    else:
        yield find_dataset(path)


def _read_vectors(root: Path) -> tuple[dict[str, list[float]], dict[str, list[float]]]:
    """Element and compound vectors (vectors.json); empty for datasets without them."""
    path = root / "vectors.json"
    if not path.is_file():
        return {}, {}
    data = _read_json(path)
    if data.get("dim") != EMBEDDING_DIM:
        raise DatasetError(f"vectors.json has dim {data.get('dim')!r}, the database expects {EMBEDDING_DIM}")
    return data.get("elements", {}), data.get("compounds", {})


def _compound_rows(
    root: Path,
    element_counts: Counter[str],
    stats: Counter[str],
    vectors: dict[str, list[float]] | None = None,
) -> Iterator[dict[str, Any]]:
    with (root / "compounds.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            card = json.loads(line)
            structure = None
            if card.get("structure"):
                path = root / "structures" / f"{card['id']}.json"
                if path.is_file():
                    structure = _read_json(path)
                    stats["structures"] += 1
            element_counts.update(card["elements"])
            stats["compounds"] += 1
            yield {
                "id": card["id"],
                "formula": card["formula"],
                "elements": card["elements"],
                "element_count": len(card["elements"]),
                "fame": int(card.get("fame") or 0),
                "kind": structure.get("kind") if structure else None,
                "names": card.get("names") or {},
                "card": card,
                "structure": structure,
                "search": search_text(card["formula"], card.get("names") or {}),
                "embedding": (vectors or {}).get(card["id"]),
            }


def _batches(rows: Iterator[dict[str, Any]], size: int = BATCH) -> Iterator[list[dict[str, Any]]]:
    batch: list[dict[str, Any]] = []
    for row in rows:
        batch.append(row)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


async def load_dataset(engine: AsyncEngine, root: Path) -> LoadReport:
    manifest = _read_json(root / "manifest.json")
    if manifest.get("schema") not in SUPPORTED_SCHEMAS:
        raise DatasetError(f"unsupported dataset schema {manifest.get('schema')!r}")
    elements: list[dict[str, Any]] = _read_json(root / "elements.json")
    pairs: list[dict[str, Any]] = _read_json(root / "pairs.json")
    classes_path = root / "classes.json"
    classes: dict[str, dict[str, Any]] = _read_json(classes_path) if classes_path.is_file() else {}

    element_vectors, compound_vectors = _read_vectors(root)

    element_counts: Counter[str] = Counter()
    stats: Counter[str] = Counter()
    async with engine.begin() as connection:
        for table in (PairRow, CompoundRow, ElementRow, ClassRow, DatasetRow):
            await connection.execute(delete(table))

        for batch in _batches(_compound_rows(root, element_counts, stats, compound_vectors)):
            await connection.execute(insert(CompoundRow), batch)

        element_rows = []
        for element in elements:
            substance = None
            if element.get("substance"):
                path = root / "structures" / f"element-{element['symbol']}.json"
                substance = _read_json(path) if path.is_file() else None
            element_rows.append(
                {
                    "z": element["z"],
                    "symbol": element["symbol"],
                    "data": element,
                    "compound_count": element_counts[element["symbol"]],
                    "substance": substance,
                    "embedding": element_vectors.get(element["symbol"]),
                }
            )
        await connection.execute(insert(ElementRow), element_rows)

        pair_rows = [{"a": p["a"], "b": p["b"], "count": p["count"], "top": p["top"]} for p in pairs]
        for start in range(0, len(pair_rows), BATCH):
            await connection.execute(insert(PairRow), pair_rows[start : start + BATCH])

        class_rows = [
            {"qid": qid, "names": info.get("names", {}), "count": info.get("count", 0)} for qid, info in classes.items()
        ]
        for start in range(0, len(class_rows), BATCH):
            await connection.execute(insert(ClassRow), class_rows[start : start + BATCH])

        await connection.execute(insert(DatasetRow), [{"version": manifest["version"], "manifest": manifest}])
        await connection.execute(text("ANALYZE"))

    return LoadReport(
        version=manifest["version"],
        elements=len(element_rows),
        compounds=stats["compounds"],
        structures=stats["structures"],
        pairs=len(pair_rows),
        classes=len(class_rows),
    )
