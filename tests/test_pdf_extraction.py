from pathlib import Path

import pymupdf as fitz

from src.extraction.pdf_extractor import compute_file_hash, extract_pdf


def _make_pdf(path: Path, pages_text: list[str]) -> None:
    doc = fitz.open()
    for text in pages_text:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_extract_pdf_preserves_page_boundaries(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path, ["Minimum annual turnover Rs. 5 crore", "Delivery period: 30 days"])

    result = extract_pdf(pdf_path)

    assert result.page_count == 2
    assert result.extraction_empty is False
    assert "turnover" in result.pages[0].text.lower()
    assert "delivery period" in result.pages[1].text.lower()
    assert result.pages[0].page == 1
    assert result.pages[1].page == 2


def test_file_hash_is_deterministic(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path, ["Hello world"])

    hash1 = compute_file_hash(pdf_path)
    hash2 = compute_file_hash(pdf_path)
    assert hash1 == hash2
    assert len(hash1) == 64


def test_extract_pdf_missing_file_raises(tmp_path):
    from src.extraction.pdf_extractor import PDFExtractionError

    try:
        extract_pdf(tmp_path / "missing.pdf")
        assert False, "expected PDFExtractionError"
    except PDFExtractionError:
        pass
