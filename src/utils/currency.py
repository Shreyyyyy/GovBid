"""Deterministic Indian currency parsing/formatting. No LLM involved."""
from __future__ import annotations

import re
from typing import Optional

LAKH = 100_000
CRORE = 10_000_000

_UNIT_MULTIPLIERS = {
    "crore": CRORE,
    "crores": CRORE,
    "cr": CRORE,
    "lakh": LAKH,
    "lakhs": LAKH,
    "lac": LAKH,
    "lacs": LAKH,
}

_NUMBER_UNIT_RE = re.compile(
    r"(?P<num>[\d,]+(?:\.\d+)?)\s*(?P<unit>crore|crores|cr|lakh|lakhs|lac|lacs)?",
    re.IGNORECASE,
)


def parse_inr(value: str | float | int | None) -> Optional[float]:
    """Convert an Indian currency string (e.g. '₹10 lakh', '1 crore',
    '₹1,25,00,000') into a plain numeric INR value.

    Returns None if the value cannot be parsed.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    text = text.replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("INR", "")
    text = text.strip()

    match = _NUMBER_UNIT_RE.search(text)
    if not match or not match.group("num"):
        return None

    num_str = match.group("num").replace(",", "")
    try:
        number = float(num_str)
    except ValueError:
        return None

    unit = match.group("unit")
    if unit:
        multiplier = _UNIT_MULTIPLIERS.get(unit.lower(), 1)
        number *= multiplier

    return number


def format_inr(value: float | int | None) -> str:
    """Format a numeric INR value using Indian-style grouping and
    lakh/crore suffixes for readability."""
    if value is None:
        return "N/A"

    value = float(value)
    if value >= CRORE:
        return f"₹{value / CRORE:.2f} crore"
    if value >= LAKH:
        return f"₹{value / LAKH:.2f} lakh"
    return f"₹{_indian_grouping(value)}"


def _indian_grouping(value: float) -> str:
    is_negative = value < 0
    value = abs(value)
    integer_part = int(value)
    decimal_part = value - integer_part

    s = str(integer_part)
    if len(s) <= 3:
        grouped = s
    else:
        last_three = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        grouped = ",".join(parts) + "," + last_three

    if decimal_part:
        grouped += f"{decimal_part:.2f}".lstrip("0")

    return ("-" if is_negative else "") + grouped
