"""All dashboard numbers come from actual database records. No fabrication."""
from __future__ import annotations

import datetime as dt
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import Bid


def get_total_bids(session: Session) -> int:
    return session.query(func.count(Bid.id)).scalar() or 0


def get_active_bids(session: Session) -> int:
    return session.query(func.count(Bid.id)).filter(Bid.status == "ACTIVE").scalar() or 0


def get_total_value(session: Session) -> float:
    return float(session.query(func.coalesce(func.sum(Bid.estimated_value), 0.0)).scalar() or 0.0)


def get_closing_soon(session: Session, within_days: int = 7) -> int:
    today = dt.date.today()
    horizon = today + dt.timedelta(days=within_days)
    return (
        session.query(func.count(Bid.id))
        .filter(Bid.bid_end_date.isnot(None), Bid.bid_end_date >= today, Bid.bid_end_date <= horizon)
        .scalar()
        or 0
    )


def get_category_breakdown(session: Session) -> list[tuple[str, int]]:
    rows = (
        session.query(Bid.category, func.count(Bid.id))
        .filter(Bid.category.isnot(None))
        .group_by(Bid.category)
        .order_by(func.count(Bid.id).desc())
        .all()
    )
    return [(r[0], r[1]) for r in rows]


def get_ministry_breakdown(session: Session) -> list[tuple[str, int]]:
    rows = (
        session.query(Bid.ministry, func.count(Bid.id))
        .filter(Bid.ministry.isnot(None))
        .group_by(Bid.ministry)
        .order_by(func.count(Bid.id).desc())
        .all()
    )
    return [(r[0], r[1]) for r in rows]


def get_state_breakdown(session: Session) -> list[tuple[str, int]]:
    rows = (
        session.query(Bid.state, func.count(Bid.id))
        .filter(Bid.state.isnot(None))
        .group_by(Bid.state)
        .order_by(func.count(Bid.id).desc())
        .all()
    )
    return [(r[0], r[1]) for r in rows]


def get_bids_over_time(session: Session) -> list[tuple[str, int]]:
    rows = session.query(Bid.created_at, Bid.id).all()
    counts: dict[str, int] = {}
    for created_at, _id in rows:
        if not created_at:
            continue
        key = created_at.strftime("%Y-%m-%d")
        counts[key] = counts.get(key, 0) + 1
    return sorted(counts.items())


def get_upcoming_bids(session: Session, limit: int = 10) -> list[Bid]:
    today = dt.date.today()
    return (
        session.query(Bid)
        .filter(Bid.bid_end_date.isnot(None), Bid.bid_end_date >= today)
        .order_by(Bid.bid_end_date.asc())
        .limit(limit)
        .all()
    )
