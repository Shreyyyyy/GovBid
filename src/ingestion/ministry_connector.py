"""Generic connector for official ministry/department tender pages.

Many ministries publish simple, static HTML tender listing pages. Since
each ministry's site differs, this connector is configured with a list of
(organization name, tender listing URL) pairs and applies a generic
"find links that look like tenders" heuristic. Sites that block requests,
require auth, or render via JavaScript are reported as unavailable.
"""
from __future__ import annotations

from typing import Any, Optional

from bs4 import BeautifulSoup

from src.ingestion.base_connector import BaseConnector, SearchResult, SourceStatus
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Configure known public, static ministry tender listing pages here.
# Left empty by default: the MVP does not assume any specific ministry
# site's structure without verification. Operators can add verified
# public pages before enabling this connector.
MINISTRY_SOURCES: list[dict[str, str]] = []

TENDER_KEYWORDS = ("tender", "bid", "procurement", "notice inviting", "nit")


class MinistryConnector(BaseConnector):
    name = "ministry"

    def health_check(self) -> SourceStatus:
        if not MINISTRY_SOURCES:
            return SourceStatus(
                source=self.name,
                reachable=False,
                message="No ministry sources configured yet.",
            )
        reachable_count = 0
        for src in MINISTRY_SOURCES:
            try:
                response = self._polite_get(src["url"])
                if response.status_code == 200:
                    reachable_count += 1
            except Exception as exc:
                logger.info("Ministry source unreachable (%s): %s", src.get("organization"), exc)
        reachable = reachable_count > 0
        return SourceStatus(
            source=self.name,
            reachable=reachable,
            message=f"{reachable_count}/{len(MINISTRY_SOURCES)} configured ministry sources reachable.",
        )

    def search(self, filters: dict[str, Any]) -> SearchResult:
        if not MINISTRY_SOURCES:
            return SearchResult(
                bids=[],
                status=SourceStatus(
                    source=self.name,
                    reachable=False,
                    message=(
                        "Unavailable for automated access: no verified public ministry "
                        "tender pages are configured for this MVP. Add entries to "
                        "MINISTRY_SOURCES in src/ingestion/ministry_connector.py, or use "
                        "manual document upload."
                    ),
                ),
            )

        bids: list[dict[str, Any]] = []
        errors: list[str] = []
        for src in MINISTRY_SOURCES:
            try:
                response = self._polite_get(src["url"])
                soup = BeautifulSoup(response.text, "lxml")
                for link in soup.find_all("a", href=True):
                    text = link.get_text(strip=True)
                    if not text or len(text) < 8:
                        continue
                    if not any(kw in text.lower() for kw in TENDER_KEYWORDS):
                        continue
                    href = link["href"]
                    if href.startswith("/"):
                        base = src["url"].split("/", 3)
                        href = f"{base[0]}//{base[2]}{href}"
                    bids.append(
                        self.normalize(
                            {
                                "bid_id": None,
                                "title": text,
                                "source_url": href,
                                "organization": src.get("organization", ""),
                                "ministry": src.get("ministry", src.get("organization", "")),
                                "status": "ACTIVE",
                            }
                        )
                    )
            except Exception as exc:
                errors.append(f"{src.get('organization', src.get('url'))}: {exc}")

        message = f"Fetched {len(bids)} listings from {len(MINISTRY_SOURCES)} ministry source(s)."
        if errors:
            message += f" {len(errors)} source(s) unavailable for automated access: {'; '.join(errors)}"

        return SearchResult(
            bids=bids,
            status=SourceStatus(source=self.name, reachable=True, message=message),
        )

    def fetch_bid(self, bid_id: str) -> Optional[dict[str, Any]]:
        return None

    def fetch_documents(self, bid: dict[str, Any]) -> list[dict[str, Any]]:
        return []
