"""PDF text extraction with a two-engine fallback strategy.

``pdfplumber`` is tried first because it preserves layout and whitespace well
for typical resume PDFs. If it returns empty text or raises, we fall back to
``pypdf`` which handles a broader range of malformed / non-standard PDFs at
the cost of layout fidelity.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import IO

import pdfplumber
from pypdf import PdfReader

__all__ = ["parse_pdf_stream", "parse_pdf_path"]

logger = logging.getLogger(__name__)

PathLike = str | Path


def parse_pdf_stream(stream: IO[bytes]) -> str:
    """Extract text from an open binary PDF stream.

    Tries ``pdfplumber`` first; on empty output or any exception, rewinds the
    stream and retries with ``pypdf``. Returns the concatenated page text
    (pages joined by ``\\n\\n``). Never raises — an empty string is returned
    if both engines fail to find any text.
    """
    try:
        with pdfplumber.open(stream) as pdf:
            pages = [(page.extract_text() or "").strip() for page in pdf.pages]
        text = "\n\n".join(p for p in pages if p)
        if text.strip():
            return text
        logger.warning("pdfplumber returned empty text; falling back to pypdf")
    except Exception as err:  # noqa: BLE001 — fallback is deliberate
        logger.warning("pdfplumber failed: %s; falling back to pypdf", err)

    stream.seek(0)
    reader = PdfReader(stream)
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(p for p in pages if p)


def parse_pdf_path(path: PathLike) -> str:
    """Extract text from a PDF file on disk.

    Raises :class:`FileNotFoundError` if the path does not exist.
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    with pdf_path.open("rb") as fh:
        return parse_pdf_stream(fh)
