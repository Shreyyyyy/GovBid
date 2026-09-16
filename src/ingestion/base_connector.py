"""Common interface for all procurement source connectors.

Every connector must be independently enabled/disableable (see
ENABLED_SOURCES in config) and must never bypass CAPTCHA, login, rate
limits or robots restrictions. When a source cannot be reached
programmatically, connectors must report a clear "unavailable" status
rather than fabricate data.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional

import requests

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

NORMALIZED_BID_FIELDS = {
    "bid_id": "",
    "title": "",
    "description": "",
    "source": "",
    "source_url": "",
    "organization": "",
    "ministry": "",
    "department": "",
    "buyer_name": "",
    "category": "",
    "subcategory": "",
    "quantity": None,
    "estimated_value": None,
    "currency": "INR",
    "bid_start_date": None,
    "bid_end_date": None,
    "status": "",
    "delivery_location": "",
    "state": "",
    "city": "",
    "eligibility": "",
    "technical_requirements": "",
    "financial_requirements": "",
    "experience_requirements": "",
    "oem_required": None,
    "mse_preference": None,
    "startup_preference": None,
    "turnover_requirement": "",
    "past_experience_requirement": "",
    "documents": [],
    "raw_data": {},
}


def empty_normalized_bid() -> dict[str, Any]:
    return {k: (v.copy() if isinstance(v, (list, dict)) else v) for k, v in NORMALIZED_BID_FIELDS.items()}


@dataclass
class SourceStatus:
    source: str
    reachable: bool
    message: str
    checked_at: float = field(default_factory=time.time)


@dataclass
class SearchResult:
    bids: list[dict[str, Any]]
    status: SourceStatus


class BaseConnector(ABC):
    """Base class every source connector must implement."""

    name: str = "base"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.user_agent})

    def _polite_get(self, url: str, **kwargs) -> requests.Response:
        """GET with configured timeout and a fixed delay to avoid aggressive
        crawling. Retries once on transient failure."""
        return self._polite_request("GET", url, **kwargs)

    def _polite_post(self, url: str, **kwargs) -> requests.Response:
        """POST with configured timeout and a fixed delay to avoid aggressive
        crawling. Retries once on transient failure."""
        return self._polite_request("POST", url, **kwargs)

    def _polite_request(self, method: str, url: str, **kwargs) -> requests.Response:
        timeout = kwargs.pop("timeout", settings.request_timeout_seconds)
        last_exc: Optional[Exception] = None
        for attempt in range(2):
            try:
                response = self.session.request(method, url, timeout=timeout, **kwargs)
                time.sleep(settings.request_delay_seconds)
                return response
            except requests.RequestException as exc:
                last_exc = exc
                time.sleep(settings.request_delay_seconds)
        raise last_exc  # type: ignore[misc]

    @abstractmethod
    def health_check(self) -> SourceStatus:
        """Check whether the source is reachable for public/permitted access."""

    @abstractmethod
    def search(self, filters: dict[str, Any]) -> SearchResult:
        """Search the source using structured filters and return normalized bids."""

    @abstractmethod
    def fetch_bid(self, bid_id: str) -> Optional[dict[str, Any]]:
        """Fetch a single bid's full detail, normalized."""

    @abstractmethod
    def fetch_documents(self, bid: dict[str, Any]) -> list[dict[str, Any]]:
        """Return document references (name, url) associated with a bid."""

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Merge raw source-specific fields onto the normalized bid schema.

        If `raw` already carries its own `raw_data` (a connector that
        pre-translates source-specific fields, like GemConnector, stashes
        the untransformed source record there), that is preserved as-is
        rather than being overwritten with the translated dict.
        """
        normalized = empty_normalized_bid()
        normalized.update({k: v for k, v in raw.items() if k in normalized})
        normalized["source"] = self.name
        normalized["raw_data"] = _json_safe(raw.get("raw_data", raw))
        return normalized


def _json_safe(value: Any) -> Any:
    """Recursively convert dates/datetimes (and other non-JSON types) so the
    result can be stored in a JSON column without raising."""
    import datetime as _dt

    if isinstance(value, (_dt.date, _dt.datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return value
