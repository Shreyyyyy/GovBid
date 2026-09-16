"""Simple, dependency-light local semantic search abstraction.

This starts as a pure-Python keyword-overlap scorer so semantic search is
never a hard requirement for basic filtering. It is deliberately modular so
a stronger backend (ChromaDB, FAISS, embeddings) can be swapped in later
without changing callers.
"""
from __future__ import annotations

import re
from typing import Iterable, Protocol

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))


class SemanticIndex(Protocol):
    def score(self, query: str, documents: Iterable[str]) -> list[float]:
        ...


class OverlapSemanticIndex:
    """Naive term-overlap (Jaccard) similarity. No external dependencies."""

    def score(self, query: str, documents: Iterable[str]) -> list[float]:
        query_tokens = _tokenize(query)
        if not query_tokens:
            return [0.0 for _ in documents]

        scores = []
        for doc in documents:
            doc_tokens = _tokenize(doc)
            if not doc_tokens:
                scores.append(0.0)
                continue
            intersection = query_tokens & doc_tokens
            union = query_tokens | doc_tokens
            scores.append(len(intersection) / len(union) if union else 0.0)
        return scores


def rank_by_semantic_similarity(query: str, items: list[dict], text_field: str = "description") -> list[dict]:
    """Rank a list of bid dicts by similarity to `query`. Non-mutating; returns
    a new list sorted descending by score, with a `_semantic_score` key added."""
    if not query:
        return items

    index = OverlapSemanticIndex()
    documents = [f"{item.get('title', '')} {item.get(text_field, '')}" for item in items]
    scores = index.score(query, documents)

    scored = list(zip(items, scores))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    result = []
    for item, score in scored:
        enriched = dict(item)
        enriched["_semantic_score"] = score
        result.append(enriched)
    return result
