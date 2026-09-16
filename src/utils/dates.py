"""Deterministic date handling. The LLM never computes dates."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Optional, Tuple


def parse_date(value: str | date | datetime | None) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip()
    if not text:
        return None

    formats = (
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%d %B %Y",
        "%d %b %Y",
    )
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


_RELATIVE_PATTERNS = [
    (re.compile(r"next\s+(\d+)\s+days?", re.IGNORECASE), lambda m, today: (today, today + timedelta(days=int(m.group(1))))),
    (re.compile(r"closing\s+this\s+week", re.IGNORECASE), lambda m, today: (today, today + timedelta(days=(6 - today.weekday())))),
    (re.compile(r"this\s+week", re.IGNORECASE), lambda m, today: (today, today + timedelta(days=(6 - today.weekday())))),
    (re.compile(r"this\s+month", re.IGNORECASE), lambda m, today: (today, _end_of_month(today))),
    (re.compile(r"today", re.IGNORECASE), lambda m, today: (today, today)),
    (re.compile(r"tomorrow", re.IGNORECASE), lambda m, today: (today + timedelta(days=1), today + timedelta(days=1))),
]


def _end_of_month(today: date) -> date:
    if today.month == 12:
        return date(today.year, 12, 31)
    next_month = date(today.year, today.month + 1, 1)
    return next_month - timedelta(days=1)


def resolve_relative_range(phrase: str, today: Optional[date] = None) -> Optional[Tuple[date, date]]:
    """Convert phrases like 'next 15 days', 'this month', 'closing this week'
    into an exact (start, end) date range using Python only."""
    if not phrase:
        return None
    today = today or date.today()
    for pattern, resolver in _RELATIVE_PATTERNS:
        match = pattern.search(phrase)
        if match:
            return resolver(match, today)
    return None


def days_until(target: date | None, today: Optional[date] = None) -> Optional[int]:
    if target is None:
        return None
    today = today or date.today()
    return (target - today).days


def is_closing_soon(target: date | None, within_days: int = 7, today: Optional[date] = None) -> bool:
    remaining = days_until(target, today)
    if remaining is None:
        return False
    return 0 <= remaining <= within_days
