"""A small vector model of the elements and compounds (the "similarity" feature).

Elements: two elements are alike when they form compounds with the same partners
(Na and K both pair with Cl, O, S…). We count how often elements meet in one compound,
turn the counts into positive pointwise mutual information (PPMI) and compress the
matrix with SVD. This is the classic distributional method behind word vectors:
"you shall know a word by the company it keeps".

Compounds: the atom-fraction-weighted average of their element vectors. Fe₂O₃ lands
next to Cr₂O₃ and Al₂O₃: similar elements in similar proportions.

The API stores the vectors in PostgreSQL (pgvector) and answers "similar" queries
with a cosine-distance index.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

import numpy as np

from .elements_table import SYMBOLS, Z_BY_SYMBOL

DIM = 16
MIN_COMPOUNDS = 3  # elements with fewer compounds get no vector: too little evidence


def cooccurrence(compositions: Iterable[Mapping[str, float]]) -> tuple[np.ndarray, np.ndarray]:
    """Element × element counts of compounds that contain both, and compounds per element."""
    size = len(SYMBOLS)
    counts = np.zeros((size, size))
    occurrences = np.zeros(size)
    for composition in compositions:
        indices = sorted({Z_BY_SYMBOL[symbol] - 1 for symbol in composition})
        for i in indices:
            occurrences[i] += 1
            for j in indices:
                if i != j:
                    counts[i, j] += 1
    return counts, occurrences


def ppmi(counts: np.ndarray) -> np.ndarray:
    total = counts.sum()
    if total == 0:
        return np.zeros_like(counts)
    rows = counts.sum(axis=1, keepdims=True)
    cols = counts.sum(axis=0, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        pmi = np.log(counts * total / (rows * cols))
    pmi[~np.isfinite(pmi)] = 0.0
    result: np.ndarray = np.maximum(pmi, 0.0)
    return result


def _normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return np.asarray(matrix / norms)


def element_vectors(compositions: list[Mapping[str, float]], dim: int = DIM) -> dict[str, list[float]]:
    """Unit vectors for elements with at least MIN_COMPOUNDS compounds."""
    counts, occurrences = cooccurrence(compositions)
    matrix = ppmi(counts)
    if not matrix.any():
        return {}
    u, s, _ = np.linalg.svd(matrix)
    k = min(dim, len(s))
    vectors = np.zeros((len(SYMBOLS), dim))
    vectors[:, :k] = u[:, :k] * np.sqrt(s[:k])
    vectors = _normalize(vectors)
    return {
        symbol: [round(float(x), 5) for x in vectors[index]]
        for index, symbol in enumerate(SYMBOLS)
        if occurrences[index] >= MIN_COMPOUNDS and np.linalg.norm(vectors[index]) > 0
    }


def compound_vector(composition: Mapping[str, float], elements: Mapping[str, list[float]]) -> list[float] | None:
    """Atom-fraction-weighted mean of the element vectors, as a unit vector."""
    total = sum(composition.values())
    if total <= 0:
        return None
    vector = np.zeros(len(next(iter(elements.values()))) if elements else DIM)
    for symbol, amount in composition.items():
        if symbol not in elements:
            return None  # an element without a vector: no reliable position
        vector += (amount / total) * np.asarray(elements[symbol])
    norm = np.linalg.norm(vector)
    if norm == 0:
        return None
    return [round(float(x), 5) for x in vector / norm]


def nearest(vectors: Mapping[str, list[float]], key: str, count: int = 6) -> list[tuple[str, float]]:
    """Most similar keys by cosine similarity (used for the report and tests)."""
    if key not in vectors:
        return []
    names = [name for name in vectors if name != key]
    matrix = np.asarray([vectors[name] for name in names])
    scores = matrix @ np.asarray(vectors[key])
    order = np.argsort(-scores)[:count]
    return [(names[i], round(float(scores[i]), 3)) for i in order]
