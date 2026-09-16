"""Connector for GeM (Government e-Marketplace) public bid information.

This talks to the same public, anonymous, session+CSRF-protected JSON
endpoint (`bidplus.gem.gov.in/all-bids-data`) that gem.gov.in's own public
"All Bids" page (`bidplus.gem.gov.in/all-bids`) uses to render bid cards for
any visitor - no login, no CAPTCHA, and robots.txt permits crawling this
path (only `/resources/` and a couple of unrelated bank-guarantee endpoints
are disallowed). We replicate exactly what a browser does: load the public
page once to obtain a session cookie and the page's CSRF token, then reuse
both for the same JSON calls the page itself makes. This is not an
authentication or anti-bot bypass - it is the site's own public contract.

If GeM changes this contract, tightens access, or a request is blocked, this
connector reports the source as unavailable rather than guessing at content
or fabricating bids.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any, Optional

import requests

from src.ingestion.base_connector import BaseConnector, SearchResult, SourceStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)

GEM_ALL_BIDS_PAGE = "https://bidplus.gem.gov.in/all-bids"
GEM_ALL_BIDS_DATA = "https://bidplus.gem.gov.in/all-bids-data"
GEM_BASE_URL = "https://bidplus.gem.gov.in"

_CSRF_RE = re.compile(r"csrf_bd_gem_nk['\"]?\s*:\s*['\"]([a-f0-9]{16,64})['\"]")

_DOC_LABEL_BY_BID_TYPE = {
    5: "showdirectradocumentPdf",
    2: "showradocumentPdf",
}
_DEFAULT_DOC_LABEL = "showbidDocument"


def _describe_connection_error(exc: Exception) -> str:
    """Distinguish a network-level block (connection refused/reset - typically
    a host's firewall rejecting a hosting provider's IP range) from other
    failures, so the real cause is visible instead of a generic traceback."""
    if isinstance(exc, requests.exceptions.ConnectionError):
        return (
            "Unavailable for automated access: could not open a connection to GeM "
            "(connection refused/reset). GeM is reachable from ordinary residential/"
            "ISP connections, so this usually means GeM's firewall is blocking this "
            "server's network range (a common anti-bot measure many Indian government "
            "sites apply to known cloud/PaaS datacenter IPs, e.g. Render, AWS, Heroku). "
            "This is not a code bug and this project does not attempt to route around "
            "it. Try running the app locally, or from infrastructure with a normal ISP "
            "egress IP, instead."
        )
    if isinstance(exc, requests.exceptions.Timeout):
        return f"Unavailable for automated access: GeM did not respond in time ({exc})."
    return f"Unavailable for automated access: {exc}"


class GemConnector(BaseConnector):
    name = "gem"

    def _fresh_session_token(self) -> Optional[str]:
        """Load the public all-bids page to obtain a session cookie (stored
        automatically in self.session) and this page's CSRF token."""
        response = self._polite_get(GEM_ALL_BIDS_PAGE)
        if response.status_code != 200:
            return None
        match = _CSRF_RE.search(response.text)
        return match.group(1) if match else None

    def health_check(self) -> SourceStatus:
        try:
            response = self._polite_get(GEM_ALL_BIDS_PAGE)
            reachable = response.status_code == 200
            message = "GeM public bid listing reachable." if reachable else f"GeM returned HTTP {response.status_code}."
            return SourceStatus(source=self.name, reachable=reachable, message=message)
        except Exception as exc:
            logger.info("GeM health check failed: %s", exc)
            return SourceStatus(source=self.name, reachable=False, message=_describe_connection_error(exc))

    def _query_page(self, token: str, param: dict[str, Any], filter_: dict[str, Any], page: Optional[int] = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"param": param, "filter": filter_}
        if page:
            payload["page"] = page

        import json as _json

        response = self._polite_post(
            GEM_ALL_BIDS_DATA,
            data={"payload": _json.dumps(payload), "csrf_bd_gem_nk": token},
            headers={
                "X-Requested-With": "XMLHttpRequest",
                "Referer": GEM_ALL_BIDS_PAGE,
                "Origin": GEM_BASE_URL,
            },
        )
        response.raise_for_status()
        return response.json()

    def search(self, filters: dict[str, Any]) -> SearchResult:
        keyword_parts = list(filters.get("keywords") or [])
        for extra in ("category", "subcategory"):
            values = filters.get(extra)
            if values:
                keyword_parts.extend(values)
        search_text = " ".join(str(k) for k in keyword_parts).strip()

        try:
            token = self._fresh_session_token()
        except Exception as exc:
            logger.warning("GeM: failed to establish session: %s", exc)
            return SearchResult(
                bids=[],
                status=SourceStatus(source=self.name, reachable=False, message=_describe_connection_error(exc)),
            )

        if not token:
            return SearchResult(
                bids=[],
                status=SourceStatus(
                    source=self.name,
                    reachable=False,
                    message="Unavailable for automated access: could not obtain GeM's public page session token (the page format may have changed).",
                ),
            )

        param: dict[str, Any] = {"searchType": "fullText"}
        if search_text:
            param["searchBid"] = search_text
        bid_filter: dict[str, Any] = {"bidStatusType": "ongoing_bids", "byType": "all"}
        if filters.get("status") == "CLOSED":
            bid_filter["bidStatusType"] = "bidrastatus"

        all_bids: list[dict[str, Any]] = []
        total_found = 0
        try:
            for page in range(1, settings_max_pages() + 1):
                data = self._query_page(token, param, bid_filter, page=page if page > 1 else None)
                if data.get("code") != 200:
                    break
                response_block = data.get("response", {}).get("response", {})
                total_found = response_block.get("numFound", total_found)
                docs = response_block.get("docs", [])
                if not docs:
                    break
                all_bids.extend(_normalize_doc(doc) for doc in docs)
                if len(all_bids) >= total_found:
                    break
        except Exception as exc:
            logger.warning("GeM search failed: %s", exc)
            status = SourceStatus(
                source=self.name,
                reachable=False,
                message=_describe_connection_error(exc),
            )
            return SearchResult(bids=[self.normalize(b) for b in all_bids], status=status)

        normalized = [self.normalize(b) for b in all_bids]
        message = f"Fetched {len(normalized)} of {total_found} matching bids from GeM (page size limited to {settings_max_pages()} pages)."
        return SearchResult(bids=normalized, status=SourceStatus(source=self.name, reachable=True, message=message))

    def fetch_bid(self, bid_id: str) -> Optional[dict[str, Any]]:
        try:
            token = self._fresh_session_token()
            if not token:
                return None
            data = self._query_page(token, {"searchBid": bid_id, "searchType": "exact"}, {"bidStatusType": "ongoing_bids", "byType": "all"})
            docs = data.get("response", {}).get("response", {}).get("docs", [])
            for doc in docs:
                if (doc.get("b_bid_number") or [None])[0] == bid_id:
                    return self.normalize(_normalize_doc(doc))
        except Exception as exc:
            logger.warning("GeM fetch_bid failed for %s: %s", bid_id, exc)
        return None

    def fetch_documents(self, bid: dict[str, Any]) -> list[dict[str, Any]]:
        url = bid.get("source_url")
        if not url:
            return []
        try:
            response = self._polite_get(url)
        except Exception as exc:
            logger.info("GeM document fetch failed for %s: %s", url, exc)
            return []

        content_type = response.headers.get("Content-Type", "").lower()
        if response.status_code != 200 or "pdf" not in content_type or not response.content:
            logger.info("GeM document unavailable for automated download: %s (status=%s, type=%s, len=%s)", url, response.status_code, content_type, len(response.content or b""))
            return []

        return [{"name": f"{bid.get('bid_id', 'bid')}.pdf", "url": url, "content": response.content}]


def settings_max_pages() -> int:
    from src.config import settings

    return max(1, settings.max_pages_per_source)


def _parse_gem_date(value: Any) -> Optional[dt.date]:
    """GeM returns ISO8601 UTC timestamps, e.g. '2026-02-27T15:20:38Z'.
    A sentinel of '-0001-11-30T00:00:00Z' means "no end date" (used for
    reverse-auction-only bids) and should be treated as unset."""
    if not value:
        return None
    if isinstance(value, list):
        value = value[0] if value else None
    if not isinstance(value, str) or value.startswith("-"):
        return None
    try:
        return dt.datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S").date()
    except ValueError:
        return None


def _first(doc: dict[str, Any], key: str) -> Any:
    value = doc.get(key)
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _normalize_doc(doc: dict[str, Any]) -> dict[str, Any]:
    bid_id = doc.get("b_id")
    bid_id = bid_id[0] if isinstance(bid_id, list) and bid_id else bid_id
    bid_type = _first(doc, "b_bid_type")
    doc_label = _DOC_LABEL_BY_BID_TYPE.get(bid_type, _DEFAULT_DOC_LABEL)

    ministry = _first(doc, "ba_official_details_minName")
    department = _first(doc, "ba_official_details_deptName")
    if department in ("NA", "", None):
        department = None

    return {
        "bid_id": _first(doc, "b_bid_number"),
        "title": _first(doc, "b_category_name") or "Untitled GeM bid",
        "description": None,
        "source_url": f"{GEM_BASE_URL}/{doc_label}/{bid_id}" if bid_id else None,
        "organization": ministry,
        "ministry": ministry,
        "department": department,
        "category": _first(doc, "b_category_name"),
        "quantity": _first(doc, "b_total_quantity"),
        "bid_start_date": _parse_gem_date(doc.get("final_start_date_sort")),
        "bid_end_date": _parse_gem_date(doc.get("final_end_date_sort")),
        "status": "ACTIVE",
        "raw_data": doc,
    }
