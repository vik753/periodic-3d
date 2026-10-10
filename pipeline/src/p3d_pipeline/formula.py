"""Chemical formula parsing and formatting.

Wikidata writes formulas with Unicode subscripts (H₂O), charges (NH₄⁺) and hydrate
dots (CuSO₄·5H₂O). This module turns them into element counts and back into
standard notations.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from .elements_table import SYMBOL_SET

_SUBSCRIPTS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_TO_SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
_SUPERSCRIPT_CHARGE = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻]+")
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_HYDRATE_SPLIT = re.compile(r"[·•∙⋅*]")
_LEADING_MULTIPLIER = re.compile(r"^(\d+(?:\.\d+)?)(?=[A-Z(\[{])")

ElementCounts = dict[str, float]


def _parse_group(text: str) -> Counter[str] | None:
    stack: list[Counter[str]] = [Counter()]
    i = 0
    while i < len(text):
        char = text[i]
        if char in "([{":
            stack.append(Counter())
            i += 1
        elif char in ")]}":
            if len(stack) == 1:
                return None
            group = stack.pop()
            i += 1
            match = _NUMBER.match(text, i)
            factor = 1.0
            if match:
                factor = float(match.group())
                i = match.end()
            for symbol, amount in group.items():
                stack[-1][symbol] += amount * factor
        elif char.isupper():
            symbol = char
            i += 1
            if i < len(text) and text[i].islower():
                symbol += text[i]
                i += 1
            if symbol in ("D", "T"):  # deuterium and tritium are hydrogen
                symbol = "H"
            if symbol not in SYMBOL_SET:
                return None
            match = _NUMBER.match(text, i)
            amount = 1.0
            if match:
                amount = float(match.group())
                i = match.end()
            stack[-1][symbol] += amount
        else:
            return None
    if len(stack) != 1 or not stack[0]:
        return None
    return stack[0]


def normalize(raw: str) -> str:
    """ASCII digits, no charges, no spaces: 'Fe₂O₃' → 'Fe2O3'."""
    text = raw.translate(_SUBSCRIPTS)
    text = _SUPERSCRIPT_CHARGE.sub("", text)
    text = text.replace(" ", "").replace(" ", "").replace(" ", "")
    return re.sub(r"[+\-−]+$", "", text)


def parse_formula(raw: str) -> ElementCounts | None:
    """Parse a formula into element counts. Returns None for variable or unknown formulas."""
    text = normalize(raw)
    if not text:
        return None
    total: Counter[str] = Counter()
    for part in _HYDRATE_SPLIT.split(text):
        if not part:
            continue
        factor = 1.0
        match = _LEADING_MULTIPLIER.match(part)
        if match:
            factor = float(match.group(1))
            part = part[match.end() :]
        counts = _parse_group(part)
        if counts is None:
            return None
        for symbol, amount in counts.items():
            total[symbol] += amount * factor
    return dict(total) if total else None


def _is_integral(counts: ElementCounts) -> bool:
    return all(abs(value - round(value)) < 1e-6 for value in counts.values())


def _format_count(value: float) -> str:
    if abs(value - round(value)) < 1e-6:
        number = round(value)
        return "" if number == 1 else str(number)
    return f"{value:g}"


def hill_formula(counts: ElementCounts) -> str:
    """Hill system: C first, then H, then alphabetical; without C all alphabetical."""
    if "C" in counts:
        order = ["C"] + (["H"] if "H" in counts else []) + sorted(k for k in counts if k not in ("C", "H"))
    else:
        order = sorted(counts)
    return "".join(f"{symbol}{_format_count(counts[symbol])}" for symbol in order)


def reduced_formula(counts: ElementCounts) -> str | None:
    """OPTIMADE chemical_formula_reduced: alphabetical, gcd-reduced integer counts."""
    if not _is_integral(counts):
        return None
    ints = {symbol: round(value) for symbol, value in counts.items()}
    divisor = 0
    for value in ints.values():
        divisor = math.gcd(divisor, value)
    divisor = divisor or 1
    parts = []
    for symbol in sorted(ints):
        count = ints[symbol] // divisor
        parts.append(symbol if count == 1 else f"{symbol}{count}")
    return "".join(parts)


def to_subscripts(formula: str) -> str:
    """'Fe2O3' → 'Fe₂O₃' (digits that follow a letter or bracket only)."""
    return re.sub(r"(?<=[A-Za-z)\]}])(\d+)", lambda m: m.group(1).translate(_TO_SUBSCRIPT), formula)


def atom_count(counts: ElementCounts) -> float:
    return sum(counts.values())


def same_proportions(a: ElementCounts, b: ElementCounts, tolerance: float = 0.02) -> bool:
    """True when two compositions have the same elements in the same ratios."""
    if set(a) != set(b) or not a:
        return False
    total_a = atom_count(a)
    total_b = atom_count(b)
    return all(abs(a[k] / total_a - b[k] / total_b) <= tolerance for k in a)
