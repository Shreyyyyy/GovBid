"""CRUD and upsert helpers for bids, applying deterministic deduplication."""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.models import Bid, SourceRecord
from src.utils.dates import parse_date
from src.utils.deduplication import dedup_key


def upsert_bid(session: Session, normalized_bid: dict[str, Any]) -> tuple[Bid, bool]:
    """Insert a normalized bid, or merge it onto an existing matching bid.

    Returns (bid, created) where created is True if a new row was inserted.
    Duplicate detection preserves multiple source URLs rather than creating
    duplicate rows.
    """
    key = dedup_key(
        normalized_bid.get("bid_id"),
        normalized_bid.get("source"),
        normalized_bid.get("source_url"),
        normalized_bid.get("title"),
        normalized_bid.get("organization"),
    )

    existing = session.query(Bid).filter(Bid.dedup_key == key).first()

    is_demo = str(normalized_bid.get("source", "")).upper() == "DEMO"

    bid_start = parse_date(normalized_bid.get("bid_start_date"))
    bid_end = parse_date(normalized_bid.get("bid_end_date"))

    fields = dict(
        bid_id=normalized_bid.get("bid_id"),
        title=normalized_bid.get("title") or "Untitled bid",
        description=normalized_bid.get("description"),
        source=normalized_bid.get("source", "unknown"),
        source_url=normalized_bid.get("source_url"),
        organization=normalized_bid.get("organization"),
        ministry=normalized_bid.get("ministry"),
        department=normalized_bid.get("department"),
        buyer_name=normalized_bid.get("buyer_name"),
        category=normalized_bid.get("category"),
        subcategory=normalized_bid.get("subcategory"),
        quantity=normalized_bid.get("quantity"),
        estimated_value=normalized_bid.get("estimated_value"),
        currency=normalized_bid.get("currency") or "INR",
        bid_start_date=bid_start,
        bid_end_date=bid_end,
        status=normalized_bid.get("status") or None,
        delivery_location=normalized_bid.get("delivery_location"),
        state=normalized_bid.get("state"),
        city=normalized_bid.get("city"),
        eligibility=normalized_bid.get("eligibility"),
        technical_requirements=normalized_bid.get("technical_requirements"),
        financial_requirements=normalized_bid.get("financial_requirements"),
        experience_requirements=normalized_bid.get("experience_requirements"),
        oem_required=normalized_bid.get("oem_required"),
        mse_preference=normalized_bid.get("mse_preference"),
        startup_preference=normalized_bid.get("startup_preference"),
        turnover_requirement=normalized_bid.get("turnover_requirement"),
        past_experience_requirement=normalized_bid.get("past_experience_requirement"),
        raw_data=normalized_bid.get("raw_data"),
        is_demo=is_demo,
    )

    if existing:
        for k, v in fields.items():
            if v not in (None, ""):
                setattr(existing, k, v)
        _add_source_url(existing, normalized_bid.get("source_url"))
        session.add(SourceRecord(bid=existing, source=fields["source"], source_url=normalized_bid.get("source_url")))
        return existing, False

    bid = Bid(dedup_key=key, **fields)
    session.add(bid)
    session.flush()
    session.add(SourceRecord(bid=bid, source=fields["source"], source_url=normalized_bid.get("source_url")))
    return bid, True


def _add_source_url(bid: Bid, url: Optional[str]) -> None:
    if not url:
        return
    urls = set(bid.additional_source_urls or [])
    if bid.source_url and bid.source_url != url:
        urls.add(bid.source_url)
    urls.add(url)
    urls.discard(None)
    bid.additional_source_urls = sorted(urls)


def get_bid(session: Session, bid_pk: int) -> Optional[Bid]:
    return session.get(Bid, bid_pk)


def list_ministries(session: Session) -> list[str]:
    rows = session.query(Bid.ministry).filter(Bid.ministry.isnot(None)).distinct().all()
    return sorted({r[0] for r in rows if r[0]})


def list_categories(session: Session) -> list[str]:
    rows = session.query(Bid.category).filter(Bid.category.isnot(None)).distinct().all()
    return sorted({r[0] for r in rows if r[0]})
