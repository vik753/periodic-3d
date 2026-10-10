"""Search text normalization. Mirrors apps/web/src/data/compoundIndex.ts (normalizeText)."""

from __future__ import annotations

import re
import unicodedata

_SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_SUPERSCRIPTS = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]")
_SPACES = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lower case, no stress marks or diacritics, "₂" → "2", "ё" → "е": "Гемати́т" → "гематит"."""
    text = text.lower().replace("ё", "е").replace("й", "и")
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if not unicodedata.combining(ch))
    text = text.translate(_SUBSCRIPTS)
    text = _SUPERSCRIPTS.sub("", text)
    return _SPACES.sub(" ", text).strip()


def search_text(formula: str, names: dict[str, str]) -> str:
    """One searchable line per compound: formula without spaces, then all names."""
    plain_formula = normalize_text(formula).replace(" ", "")
    return " | ".join([plain_formula, *(normalize_text(name) for name in names.values() if name)])
