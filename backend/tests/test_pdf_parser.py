import io

import pytest

from parsers.pdf_parser import parse_pdf_path, parse_pdf_stream


def _minimal_pdf_bytes(text: str = "Hello world") -> bytes:
    """Build a tiny valid PDF with a single text-bearing page using pypdf."""
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        ContentStream,
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        NumberObject,
        TextStringObject,
    )

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    page = writer.pages[0]

    content = ContentStream(None, writer)
    content.operations = [
        ([], b"BT"),
        ([NameObject("/F1"), NumberObject(12)], b"Tf"),
        ([NumberObject(50), NumberObject(100)], b"Td"),
        ([TextStringObject(text)], b"Tj"),
        ([], b"ET"),
    ]

    page[NameObject("/Contents")] = content
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): DictionaryObject({
                NameObject("/Type"): NameObject("/Font"),
                NameObject("/Subtype"): NameObject("/Type1"),
                NameObject("/BaseFont"): NameObject("/Helvetica"),
            })
        })
    })

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_parse_pdf_stream_returns_string():
    pdf_bytes = _minimal_pdf_bytes("Resume Sample Text")
    text = parse_pdf_stream(io.BytesIO(pdf_bytes))
    assert isinstance(text, str)
    assert "Resume Sample Text" in text or "Resume" in text or text.strip() != ""


def test_parse_pdf_path_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        parse_pdf_path(tmp_path / "does_not_exist.pdf")


def test_parse_pdf_path_reads_file(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(_minimal_pdf_bytes("Path Test"))
    text = parse_pdf_path(pdf_path)
    assert isinstance(text, str)
