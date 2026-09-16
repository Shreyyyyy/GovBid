"""Connector for the Central Public Procurement Portal (eprocure.gov.in).

Investigated directly against the live site: every tender-listing view
(`FrontEndLatestActiveTenders`, `FrontEndTendersByOrganisation`,
`FrontEndListTendersbyDate`, etc.) renders a CAPTCHA image and requires
POSTing a solved captcha value before it will return any tender rows
("Provide Captcha and click on Search button to list all active tenders.").
There is no way to retrieve actual tender data from CPPP without solving
that CAPTCHA.

Per this project's access rules, CAPTCHAs are never bypassed or automated.
This connector therefore performs a reachability check only and reports the
source as unavailable for automated *data* access, while still surfacing the
public URL so a user can search CPPP manually in a browser.
"""
from __future__ import annotations

from typing import Any, Optional

from src.ingestion.base_connector import BaseConnector, SearchResult, SourceStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)

CPPP_BASE_URL = "https://eprocure.gov.in"
CPPP_LATEST_TENDERS_URL = f"{CPPP_BASE_URL}/eprocure/app?page=FrontEndLatestActiveTenders&service=page"


class CpppConnector(BaseConnector):
    name = "cppp"

    def health_check(self) -> SourceStatus:
        try:
            response = self._polite_get(CPPP_LATEST_TENDERS_URL)
            reachable = response.status_code == 200
            message = "CPPP reachable." if reachable else f"CPPP returned HTTP {response.status_code}."
            return SourceStatus(source=self.name, reachable=reachable, message=message)
        except Exception as exc:
            logger.info("CPPP health check failed: %s", exc)
            return SourceStatus(source=self.name, reachable=False, message=f"CPPP unreachable: {exc}")

    def search(self, filters: dict[str, Any]) -> SearchResult:
        status = self.health_check()
        message = (
            "Unavailable for automated access: every CPPP tender-listing page requires "
            "solving a CAPTCHA before it returns results ('Provide Captcha and click on "
            "Search button to list all active tenders.'). This project does not bypass "
            f"CAPTCHAs. Search manually at {CPPP_LATEST_TENDERS_URL}"
        )
        return SearchResult(bids=[], status=SourceStatus(source=self.name, reachable=status.reachable, message=message))

    def fetch_bid(self, bid_id: str) -> Optional[dict[str, Any]]:
        return None

    def fetch_documents(self, bid: dict[str, Any]) -> list[dict[str, Any]]:
        return []
