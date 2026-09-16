"""PDF download + text extraction with page-level traceability and an OCR
fallback where practical. Downloads are size/type validated."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests

from src.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

ALLOWED_CONTENT_TYPES = ("application/pdf", "application/octet-stream")


@dataclass
class ExtractedPage:
    page: int
    text: str


@dataclass
class ExtractionResult:
    local_path: str
    file_hash: str
    page_count: int
    pages: List[ExtractedPage] = field(default_factory=list)
    extraction_empty: bool = False
    used_ocr: bool = False


class PDFExtractionError(RuntimeError):
    pass


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise PDFExtractionError(f"Unsupported URL scheme: {parsed.scheme}")


def download_pdf(url: str) -> Path:
    """Download a PDF with a timeout and a hard size limit. Returns local path."""
    from src.config import DOCUMENTS_DIR

    _validate_url(url)
    dest_dir = DOCUMENTS_DIR
    dest_dir.mkdir(parents=True, exist_ok=True)

    headers = {"User-Agent": settings.user_agent}
    max_bytes = settings.max_download_size_mb * 1024 * 1024

    with requests.get(url, headers=headers, timeout=settings.request_timeout_seconds, stream=True) as resp:
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type and content_type not in ALLOWED_CONTENT_TYPES and "pdf" not in content_type:
            raise PDFExtractionError(f"Unexpected content type: {content_type}")

        filename = Path(urlparse(url).path).name or "document.pdf"
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        dest_path = dest_dir / filename

        total = 0
        with open(dest_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                total += len(chunk)
                if total > max_bytes:
                    fh.close()
                    dest_path.unlink(missing_ok=True)
                    raise PDFExtractionError(
                        f"Download exceeded max size of {settings.max_download_size_mb}MB"
                    )
                fh.write(chunk)

    return dest_path


def compute_file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def extract_text_pymupdf(path: Path) -> List[ExtractedPage]:
    import pymupdf as fitz

    pages: List[ExtractedPage] = []
    with fitz.open(path) as doc:
        for i, page in enumerate(doc, start=1):
            pages.append(ExtractedPage(page=i, text=page.get_text("text") or ""))
    return pages


def extract_text_pdfplumber(path: Path) -> List[ExtractedPage]:
    import pdfplumber

    pages: List[ExtractedPage] = []
    with pdfplumber.open(path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages.append(ExtractedPage(page=i, text=page.extract_text() or ""))
    return pages


def extract_text_ocr(path: Path) -> List[ExtractedPage]:
    """Best-effort OCR fallback. Returns [] if OCR dependencies are unavailable
    so callers can degrade gracefully rather than crash."""
    try:
        import pymupdf as fitz  # for rendering pages to images
        import pytesseract
        from PIL import Image
        import io
    except ImportError:
        logger.info("OCR dependencies not installed; skipping OCR fallback.")
        return []

    pages: List[ExtractedPage] = []
    try:
        with fitz.open(path) as doc:
            for i, page in enumerate(doc, start=1):
                pix = page.get_pixmap(dpi=200)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                text = pytesseract.image_to_string(image)
                pages.append(ExtractedPage(page=i, text=text or ""))
    except Exception as exc:  # pragma: no cover - OCR engine may be missing at runtime
        logger.warning("OCR fallback failed: %s", exc)
        return []
    return pages


def extract_pdf(path: Path) -> ExtractionResult:
    """Extract text from a local PDF file, preserving page boundaries and
    falling back through PyMuPDF -> pdfplumber -> OCR if extraction is empty."""
    if not path.exists():
        raise PDFExtractionError(f"File not found: {path}")

    file_hash = compute_file_hash(path)

    pages: List[ExtractedPage] = []
    try:
        pages = extract_text_pymupdf(path)
    except Exception as exc:
        logger.warning("PyMuPDF extraction failed: %s", exc)

    if not any(p.text.strip() for p in pages):
        try:
            pdfplumber_pages = extract_text_pdfplumber(path)
            if any(p.text.strip() for p in pdfplumber_pages):
                pages = pdfplumber_pages
        except Exception as exc:
            logger.warning("pdfplumber extraction failed: %s", exc)

    used_ocr = False
    if not any(p.text.strip() for p in pages):
        ocr_pages = extract_text_ocr(path)
        if ocr_pages:
            pages = ocr_pages
            used_ocr = True

    extraction_empty = not any(p.text.strip() for p in pages)

    return ExtractionResult(
        local_path=str(path),
        file_hash=file_hash,
        page_count=len(pages),
        pages=pages,
        extraction_empty=extraction_empty,
        used_ocr=used_ocr,
    )


def download_and_extract(url: str) -> ExtractionResult:
    path = download_pdf(url)
    return extract_pdf(path)
