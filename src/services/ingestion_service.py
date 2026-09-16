"""Runs source connectors, deduplicates results, stores them, and logs
each ingestion run for the Admin page."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from src.config import DOCUMENTS_DIR, settings
from src.extraction.pdf_extractor import PDFExtractionError, extract_pdf
from src.ingestion.base_connector import BaseConnector
from src.ingestion.cppp_connector import CpppConnector
from src.ingestion.demo_connector import DemoConnector
from src.ingestion.gem_connector import GemConnector
from src.ingestion.ministry_connector import MinistryConnector
from src.models import Bid, BidDocument, IngestionLog
from src.services.bid_service import upsert_bid
from src.utils.logging import get_logger

logger = get_logger(__name__)

_CONNECTOR_REGISTRY: dict[str, type[BaseConnector]] = {
    "gem": GemConnector,
    "cppp": CpppConnector,
    "ministry": MinistryConnector,
    "demo": DemoConnector,
}


def get_enabled_connectors(include_demo: bool = False) -> dict[str, BaseConnector]:
    names = list(settings.enabled_sources)
    if include_demo and "demo" not in names:
        names.append("demo")
    connectors = {}
    for name in names:
        cls = _CONNECTOR_REGISTRY.get(name.lower())
        if cls:
            connectors[name.lower()] = cls()
    return connectors


def run_source(session: Session, source_name: str, filters: Optional[dict] = None) -> IngestionLog:
    cls = _CONNECTOR_REGISTRY.get(source_name.lower())
    if not cls:
        log = IngestionLog(source=source_name, status="FAILED", message=f"Unknown source: {source_name}")
        session.add(log)
        session.flush()
        return log

    connector = cls()
    filters = filters or {}

    try:
        result = connector.search(filters)
    except Exception as exc:
        logger.error("Ingestion failed for %s: %s", source_name, exc)
        log = IngestionLog(source=source_name, status="FAILED", message=str(exc))
        session.add(log)
        session.flush()
        return log

    new_records = 0
    failed_records = 0
    matched_bid_ids: list[int] = []
    for raw_bid in result.bids:
        try:
            bid_obj, created = upsert_bid(session, raw_bid)
            session.flush()
            matched_bid_ids.append(bid_obj.id)
            if created:
                new_records += 1
        except Exception as exc:
            session.rollback()
            failed_records += 1
            logger.error("Failed to store bid from %s: %s", source_name, exc)

    if not result.status.reachable:
        status = "UNAVAILABLE"
    elif "unavailable for automated access" in (result.status.message or "").lower():
        status = "UNAVAILABLE"
    else:
        status = "OK"
    log = IngestionLog(
        source=source_name,
        status=status,
        records_found=len(result.bids),
        new_records=new_records,
        failed_records=failed_records,
        message=result.status.message,
    )
    session.add(log)
    session.flush()
    # Not a mapped column - a transient hint for callers (e.g. the search
    # page) that want exactly the bids this run touched, without re-deriving
    # relevance via local keyword matching (the source's own search already
    # did that, often more accurately than a substring match on our stored
    # fields would).
    log.matched_bid_ids = matched_bid_ids
    return log


def run_all_sources(session: Session, filters: Optional[dict] = None) -> list[IngestionLog]:
    logs = []
    for name in settings.enabled_sources:
        logs.append(run_source(session, name, filters))
    return logs


def load_demo_data(session: Session) -> IngestionLog:
    return run_source(session, "demo")


def fetch_documents_for_bid(session: Session, bid: Bid) -> list[BidDocument]:
    """On-demand document fetch for a single bid (not run in bulk during
    ingestion, to keep source polling polite/non-aggressive). Downloads are
    saved locally, hashed, and text-extracted with page boundaries preserved."""
    cls = _CONNECTOR_REGISTRY.get((bid.source or "").lower())
    if not cls:
        return []

    connector = cls()
    bid_dict = {"bid_id": bid.bid_id, "source_url": bid.source_url, "source": bid.source}
    try:
        docs = connector.fetch_documents(bid_dict)
    except Exception as exc:
        logger.warning("Failed to fetch documents for bid %s: %s", bid.id, exc)
        return []

    created: list[BidDocument] = []
    existing_hashes = {d.file_hash for d in bid.documents if d.file_hash}

    for doc in docs:
        content = doc.get("content")
        if not content:
            continue

        safe_name = "".join(c for c in doc["name"] if c.isalnum() or c in "._-") or "document.pdf"
        dest = DOCUMENTS_DIR / f"bid{bid.id}_{safe_name}"
        dest.write_bytes(content)

        try:
            result = extract_pdf(dest)
        except PDFExtractionError as exc:
            logger.warning("Extraction failed for %s: %s", dest, exc)
            continue

        if result.file_hash in existing_hashes:
            continue

        bid_doc = BidDocument(
            bid=bid,
            name=doc["name"],
            doc_type="PDF",
            source_url=doc.get("url"),
            local_path=str(dest),
            file_hash=result.file_hash,
            page_count=result.page_count,
            extraction_empty=result.extraction_empty,
            used_ocr=result.used_ocr,
            extracted_pages=[{"page": p.page, "text": p.text} for p in result.pages],
        )
        session.add(bid_doc)
        created.append(bid_doc)

    session.flush()
    return created


def latest_logs(session: Session, limit: int = 20) -> list[IngestionLog]:
    return (
        session.query(IngestionLog)
        .order_by(IngestionLog.run_at.desc())
        .limit(limit)
        .all()
    )
