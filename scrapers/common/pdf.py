"""PDF text extraction.

No OCR in this stage. Image-only PDFs return an empty string and log a
warning; the caller decides whether to record the miss.
"""

from __future__ import annotations

import hashlib
import io
import logging

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

log = logging.getLogger(__name__)


def get_pdf_hash(pdf_bytes: bytes) -> str:
    """SHA-256 of the raw bytes. Used to detect when a standing order has
    been updated since the last scrape.
    """
    return hashlib.sha256(pdf_bytes).hexdigest()


def extract_text(pdf_bytes: bytes) -> str:
    """Return all text from a PDF, best-effort. Never raises on parse
    errors - returns an empty string and logs instead.
    """
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except PdfReadError as e:
        log.warning("could not open PDF: %s", e)
        return ""

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except (FileNotDecryptedError, NotImplementedError) as e:
            log.warning("PDF is encrypted and empty password failed: %s", e)
            return ""

    parts: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            parts.append(page.extract_text() or "")
        except Exception as e:
            log.warning("could not extract text from page %d: %s", i, e)
            parts.append("")

    text = "\n".join(parts).strip()
    if not text:
        log.warning("PDF yielded no extractable text (image-only?); skipping")
    return text
