import io
import logging
from typing import List, Tuple

from parsers.pdf_parser import parse_pdf_stream

logger = logging.getLogger(__name__)


def ingest_resume_bytes(items: List[Tuple[str, bytes]]) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for filename, blob in items:
        try:
            text = parse_pdf_stream(io.BytesIO(blob))
        except Exception:
            logger.exception("Failed to parse %s", filename)
            text = ""
        out.append((filename, text))
    return out
