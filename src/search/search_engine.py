"""Orchestrates the search pipeline:

structured filters (deterministic) -> keyword matching (already part of
structured filters) -> optional semantic ranking -> results.

Groq is never asked to filter or sort the dataset directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from src.ai.query_parser import ParsedQuery, QueryParser
from src.models import Bid
from src.search.filters import apply_filters
from src.search.semantic_search import rank_by_semantic_similarity


@dataclass
class SearchResponse:
    bids: list[Bid]
    parsed_query: ParsedQuery
    total: int


class SearchEngine:
    def __init__(self, query_parser: Optional[QueryParser] = None):
        self._query_parser = query_parser or QueryParser()

    def search(self, session: Session, natural_language_query: str, use_semantic: bool = True) -> SearchResponse:
        parsed = self._query_parser.parse(natural_language_query)
        return self.search_with_filters(session, parsed, use_semantic=use_semantic)

    def search_with_filters(self, session: Session, parsed: ParsedQuery, use_semantic: bool = True) -> SearchResponse:
        query = session.query(Bid)
        query = apply_filters(query, parsed)
        results = query.order_by(Bid.bid_end_date.asc().nullslast()).all()

        if use_semantic and parsed.semantic_query:
            dicts = [_bid_to_dict(b) for b in results]
            ranked = rank_by_semantic_similarity(parsed.semantic_query, dicts)
            id_to_bid = {b.id: b for b in results}
            results = [id_to_bid[d["id"]] for d in ranked if d.get("_semantic_score", 0) > 0] or results

        return SearchResponse(bids=results, parsed_query=parsed, total=len(results))


def _bid_to_dict(bid: Bid) -> dict:
    return {
        "id": bid.id,
        "title": bid.title,
        "description": bid.description or "",
    }
