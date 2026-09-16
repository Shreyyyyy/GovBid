"""Deterministic structured filtering against SQLite/SQLAlchemy.

The LLM never filters data directly - it only produces the ParsedQuery
object consumed here. All comparisons, date math, and numeric range checks
happen in Python/SQL.
"""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Query

from src.ai.query_parser import ParsedQuery
from src.models import Bid
from src.utils.dates import parse_date, resolve_relative_range


def apply_filters(query: Query, parsed: ParsedQuery) -> Query:
    """Apply a ParsedQuery's structured filters to a SQLAlchemy Query[Bid]."""

    for kw in parsed.keywords:
        like = f"%{kw}%"
        query = query.filter(
            or_(Bid.title.ilike(like), Bid.description.ilike(like), Bid.category.ilike(like))
        )

    if parsed.organization:
        query = query.filter(or_(*[Bid.organization.ilike(f"%{o}%") for o in parsed.organization]))
    if parsed.ministry:
        query = query.filter(or_(*[Bid.ministry.ilike(f"%{m}%") for m in parsed.ministry]))
    if parsed.department:
        query = query.filter(or_(*[Bid.department.ilike(f"%{d}%") for d in parsed.department]))
    if parsed.category:
        query = query.filter(or_(*[Bid.category.ilike(f"%{c}%") for c in parsed.category]))
    if parsed.subcategory:
        query = query.filter(or_(*[Bid.subcategory.ilike(f"%{s}%") for s in parsed.subcategory]))
    if parsed.state:
        query = query.filter(or_(*[Bid.state.ilike(f"%{s}%") for s in parsed.state]))
    if parsed.city:
        query = query.filter(or_(*[Bid.city.ilike(f"%{c}%") for c in parsed.city]))

    if parsed.status:
        query = query.filter(Bid.status == parsed.status)

    if parsed.min_value is not None:
        query = query.filter(Bid.estimated_value >= parsed.min_value)
    if parsed.max_value is not None:
        query = query.filter(Bid.estimated_value <= parsed.max_value)

    if parsed.min_quantity is not None:
        query = query.filter(Bid.quantity >= parsed.min_quantity)
    if parsed.max_quantity is not None:
        query = query.filter(Bid.quantity <= parsed.max_quantity)

    closing_after = _resolve_date_bound(parsed.closing_after)
    closing_before = _resolve_date_bound(parsed.closing_before)

    if parsed.semantic_query:
        relative_range = resolve_relative_range(parsed.semantic_query)
        if relative_range:
            closing_after = closing_after or relative_range[0]
            closing_before = closing_before or relative_range[1]

    if closing_after is not None:
        query = query.filter(Bid.bid_end_date >= closing_after)
    if closing_before is not None:
        query = query.filter(Bid.bid_end_date <= closing_before)

    return query


def _resolve_date_bound(value: Optional[str]) -> Optional[dt.date]:
    if not value:
        return None
    direct = parse_date(value)
    if direct:
        return direct
    relative = resolve_relative_range(value)
    if relative:
        return relative[1]
    return None
