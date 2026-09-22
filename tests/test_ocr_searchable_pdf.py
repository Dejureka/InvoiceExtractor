"""Standalone OCR → searchable PDF (ocr_out / {stem}.ocr.pdf)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from invoice_extractor.ocr import (
    OCR_OUTPUT_SUFFIX,
    default_ocr_out_dir,
    ocr_output_name,
    pdf_to_searchable_pdf,
    resolve_ocr_lang,
    tesseract_available,
)

CASE7_INV = Path("/workspace/bhc_cases_round/bhc/case7/invoice309.pdf")


def test_ocr_output_name():
    assert ocr_output_name(Path("foo.pdf")) == "foo.ocr.pdf"
    assert ocr_output_name(Path("/tmp/bar.PDF")) == f"bar{OCR_OUTPUT_SUFFIX}"


def test_default_ocr_out_dir(tmp_path, monkeypatch):
    monkeypatch.setattr("invoice_extractor.ocr.app_root", lambda: tmp_path)
    d = default_ocr_out_dir()
    assert d == tmp_path / "ocr_out"
    # not created until export
    assert not d.exists()
    assert default_ocr_out_dir(tmp_path / "custom_root") == tmp_path / "custom_root" / "ocr_out"


def test_resolve_ocr_lang_prefers_eng_and_optional_chinese(tmp_path):
    td = tmp_path / "tessdata"
    td.mkdir()
    (td / "eng.traineddata").write_bytes(b"x")
    (td / "chi_tra.traineddata").write_bytes(b"x")
    fake_bin = tmp_path / "tesseract"
    fake_bin.write_text("#!/bin/sh\n")
    with patch("invoice_extractor.ocr._tessdata_dir", return_value=td):
        assert resolve_ocr_lang(fake_bin) == "eng+chi_tra"


def test_pdf_to_searchable_pdf_mocked(tmp_path):
    """Unit path without real tesseract: render + per-page pdf + merge."""
    src = tmp_path / "scan.pdf"
    src.write_bytes(b"%PDF-1.4 fake")
    out_dir = tmp_path / "ocr_out"

    page_png = tmp_path / "page_0000.png"
    page_png.write_bytes(b"png")
    page_pdf = tmp_path / "page_0000.pdf"
    page_pdf.write_bytes(b"%PDF-1.4 page")

    with patch("invoice_extractor.ocr.find_tesseract", return_value=Path("/usr/bin/tesseract")):
        with patch("invoice_extractor.ocr.resolve_ocr_lang", return_value="eng"):
            with patch("invoice_extractor.ocr.render_pdf_pages", return_value=[page_png]):
                with patch(
                    "invoice_extractor.ocr._run_tesseract_pdf",
                    return_value=page_pdf,
                ) as run_pdf:
                    with patch(
                        "invoice_extractor.ocr._merge_pdfs_pymupdf",
                        side_effect=lambda pages, dest: (
                            dest.write_bytes(b"%PDF-1.4 merged"),
                            dest,
                        )[1],
                    ) as merge:
                        dest = pdf_to_searchable_pdf(src, out_dir)
                        assert dest == out_dir / "scan.ocr.pdf"
                        assert dest.is_file()
                        run_pdf.assert_called_once()
                        merge.assert_called_once()


@pytest.mark.skipif(not CASE7_INV.is_file(), reason="case7 invoice309.pdf missing")
@pytest.mark.skipif(not tesseract_available(), reason="tesseract not installed")
def test_searchable_pdf_smoke_one_page(tmp_path):
    """Live smoke: one scan page → searchable PDF with extractable text."""
    import pymupdf

    # Build a 1-page PDF from the first page of the scan sample
    src_doc = pymupdf.open(CASE7_INV)
    one = pymupdf.open()
    try:
        one.insert_pdf(src_doc, from_page=0, to_page=0)
        one_path = tmp_path / "invoice309_p1.pdf"
        one.save(str(one_path))
    finally:
        one.close()
        src_doc.close()

    dest = pdf_to_searchable_pdf(one_path, tmp_path / "ocr_out", lang="eng", dpi=150)
    assert dest.is_file()
    assert dest.name == "invoice309_p1.ocr.pdf"
    assert dest.stat().st_size > 1000

    out = pymupdf.open(dest)
    try:
        text = out[0].get_text()
    finally:
        out.close()
    # Scan invoice should yield some Latin / digits after OCR
    assert len(text.strip()) > 10
