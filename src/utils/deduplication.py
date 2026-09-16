"""Deterministic bid deduplication. No LLM involved.

Dedup precedence:
1. bid_id (exact)
2. source + bid_id
3. canonical URL
4. content hash
5. normalized title + organization fallback
"""
from __future__ import annotations

import hashlib
import re
from typing import Iterable, Optional


def normalize_title(title: str | None) -> str:
    if not title:
        return ""
    text = title.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def content_hash(*parts: str | None) -> str:
    joined = "|".join((p or "").strip().lower() for p in parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def dedup_key(
    bid_id: str | None,
    source: str | None,
    source_url: str | None,
    title: str | None,
    organization: str | None,
) -> str:
    """Return the strongest available identity key for a bid."""
    if bid_id:
        return f"bid_id:{bid_id.strip().lower()}"
    if source and bid_id:
        return f"source_bid:{source.strip().lower()}:{bid_id.strip().lower()}"
    if source_url:
        return f"url:{source_url.strip().lower().rstrip('/')}"
    norm_title = normalize_title(title)
    norm_org = normalize_title(organization)
    if norm_title and norm_org:
        return f"title_org:{norm_title}::{norm_org}"
    return f"hash:{content_hash(title, organization, source_url)}"


def find_duplicate(new_bid: dict, existing_bids: Iterable[dict]) -> Optional[dict]:
    """Given a normalized bid dict and an iterable of existing normalized
    bid dicts, return the existing bid that matches, or None."""
    new_key = dedup_key(
        new_bid.get("bid_id"),
        new_bid.get("source"),
        new_bid.get("source_url"),
        new_bid.get("title"),
        new_bid.get("organization"),
    )
    for existing in existing_bids:
        existing_key = dedup_key(
            existing.get("bid_id"),
            existing.get("source"),
            existing.get("source_url"),
            existing.get("title"),
            existing.get("organization"),
        )
        if existing_key == new_key:
            return existing
    return None
