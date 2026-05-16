import logging
from pathlib import Path
from typing import IO, Union

import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


def parse_pdf_stream(stream: IO[bytes]) -> str:
    try:
        with pdfplumber.open(stream) as pdf:
            pages = [(page.extract_text() or "").strip() for page in pdf.pages]
        text = "\n\n".join(p for p in pages if p)
        if text.strip():
            return text
        logger.warning("pdfplumber returned empty text; falling back to pypdf")
    except Exception as err:
        logger.warning("pdfplumber failed: %s; falling back to pypdf", err)

    stream.seek(0)
    reader = PdfReader(stream)
    pages = [(page.extract_text() or "").strip() for page in reader.pages]
    return "\n\n".join(p for p in pages if p)


def parse_pdf_path(path: PathLike) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"PDF not found: {p}")
    with p.open("rb") as fh:
        return parse_pdf_stream(fh)
