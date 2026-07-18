"""
PDF text extraction.

Uses PyMuPDF (fitz) because it is fast, dependency-light, and gives reliable
per-page text plus page count without external system binaries (unlike
poppler-based tools), which matters for constrained free-tier deploy targets.
"""
import logging

import fitz  # PyMuPDF

from app.core.exceptions import EmptyDocumentError, InvalidPDFError

logger = logging.getLogger(__name__)


class PageContent:
    __slots__ = ("page_number", "text")

    def __init__(self, page_number: int, text: str):
        self.page_number = page_number
        self.text = text


def extract_pages(file_path: str, filename: str) -> list[PageContent]:
    """
    Extract text from every page of a PDF.

    Returns a list of PageContent (1-indexed page numbers). Raises
    InvalidPDFError if the file can't be opened, or EmptyDocumentError if no
    page yields any extractable text (e.g. a scanned/image-only PDF).
    """
    try:
        doc = fitz.open(file_path)
    except Exception as exc:
        logger.warning("Failed to open PDF '%s': %s", filename, exc)
        raise InvalidPDFError(f"'{filename}' could not be opened as a PDF: {exc}") from exc

    pages: list[PageContent] = []
    total_pages = doc.page_count
    try:
        for i in range(total_pages):
            page = doc.load_page(i)
            text = page.get_text("text").strip()
            if text:
                pages.append(PageContent(page_number=i + 1, text=text))
    finally:
        doc.close()

    if not pages:
        raise EmptyDocumentError(filename)

    logger.info("Extracted text from %d/%d pages of '%s'", len(pages), total_pages, filename)
    return pages


def get_page_count(file_path: str) -> int:
    with fitz.open(file_path) as doc:
        return doc.page_count
