"""Natural language -> structured filters.

The LLM only extracts filters; it never decides which bids match. Actual
filtering happens in src.search.filters against SQLite.
"""
from __future__ import annotations

from typing import Any, List, Optional

from pydantic import BaseModel, Field, field_validator

from src.ai.groq_client import GroqClient, GroqClientError
from src.ai.prompts import QUERY_PARSER_SYSTEM_PROMPT
from src.utils.currency import parse_inr
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ParsedQuery(BaseModel):
    keywords: List[str] = Field(default_factory=list)
    organization: List[str] = Field(default_factory=list)
    ministry: List[str] = Field(default_factory=list)
    department: List[str] = Field(default_factory=list)
    category: List[str] = Field(default_factory=list)
    subcategory: List[str] = Field(default_factory=list)
    state: List[str] = Field(default_factory=list)
    city: List[str] = Field(default_factory=list)
    status: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    closing_after: Optional[str] = None
    closing_before: Optional[str] = None
    semantic_query: Optional[str] = None

    @field_validator("status")
    @classmethod
    def _normalize_status(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        v = v.strip().upper()
        return v if v in ("ACTIVE", "CLOSED", "UPCOMING") else None

    @field_validator("min_value", "max_value", "min_quantity", "max_quantity", mode="before")
    @classmethod
    def _coerce_numeric(cls, v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        if isinstance(v, (int, float)):
            return float(v)
        parsed = parse_inr(v)
        return parsed

    @field_validator("keywords", "organization", "ministry", "department", "category", "subcategory", "state", "city", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return []


def _empty_payload() -> dict:
    return {
        "keywords": [],
        "organization": [],
        "ministry": [],
        "department": [],
        "category": [],
        "subcategory": [],
        "state": [],
        "city": [],
        "status": None,
        "min_value": None,
        "max_value": None,
        "min_quantity": None,
        "max_quantity": None,
        "closing_after": None,
        "closing_before": None,
        "semantic_query": None,
    }


class QueryParser:
    """Parses natural-language procurement queries into ParsedQuery via Groq."""

    def __init__(self, client: Optional[GroqClient] = None):
        self._client = client

    def _get_client(self) -> GroqClient:
        if self._client is None:
            self._client = GroqClient()
        return self._client

    def parse(self, query: str) -> ParsedQuery:
        query = (query or "").strip()
        if not query:
            return ParsedQuery()

        try:
            client = self._get_client()
            payload = client.structured_output(
                system_prompt=QUERY_PARSER_SYSTEM_PROMPT,
                user_prompt=query,
            )
        except GroqClientError as exc:
            logger.warning("Falling back to keyword-only parsing: %s", exc)
            payload = _empty_payload()
            payload["keywords"] = [w for w in query.split() if len(w) > 2]

        merged = _empty_payload()
        if isinstance(payload, dict):
            merged.update({k: v for k, v in payload.items() if k in merged})

        return ParsedQuery.model_validate(merged)
