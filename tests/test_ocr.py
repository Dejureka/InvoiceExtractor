"""OCR fallback: empty text layer → tesseract → same rules_engine path."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from invoice_extractor.ocr import OCR_BACKEND, find_tesseract, is_ocr_backend, tesseract_available
from invoice_extractor.rules_engine import extract_invoice
from invoice_extractor.text_layer import backend_warning, extract_layout_text, extract_text

CASE7_INV = Path("/workspace/bhc_cases_round/bhc/case7/invoice309.pdf")
CASE7_PKL = Path("/workspace/bhc_cases_round/bhc/case7/packing309.pdf")


def test_is_ocr_backend():
    assert is_ocr_backend("ocr/tesseract")
    assert is_ocr_backend("OCR/Tesseract")
    assert not is_ocr_backend("pdftotext -layout")
    assert not is_ocr_backend("pdftotext -layout+ocr_failed")


def test_backend_warning_ocr():
    w = backend_warning("ocr/tesseract")
    assert w and "OCR used" in w
    assert "tesseract" in w.lower()


def test_extract_text_skips_ocr_when_layer_present():
    """Non-empty layer must not invoke OCR."""
    with patch("invoice_extractor.text_layer.extract_layout_text", return_value=("hello", "pdftotext -layout", False)):
        with patch("invoice_extractor.text_layer.try_ocr_pdf") as ocr:
            text, backend, needs = extract_text("dummy.pdf", allow_ocr=True)
            assert text == "hello"
            assert backend == "pdftotext -layout"
            assert needs is False
            ocr.assert_not_called()


def test_extract_text_ocr_fallback_hook():
    """Empty layer → OCR text feeds through with ocr/tesseract backend."""
    with patch(
        "invoice_extractor.text_layer.extract_layout_text",
        return_value=("", "pdftotext -layout", True),
    ):
        with patch(
            "invoice_extractor.text_layer.try_ocr_pdf",
            return_value=("INVOICE NO: 123\nTOTALS: 1.00", OCR_BACKEND, None),
        ):
            text, backend, needs = extract_text("scan.pdf", allow_ocr=True)
            assert "INVOICE" in text
            assert backend == OCR_BACKEND
            assert needs is False


def test_extract_text_ocr_failure_keeps_needs_ocr():
    with patch(
        "invoice_extractor.text_layer.extract_layout_text",
        return_value=("", "pdftotext -layout", True),
    ):
        with patch(
            "invoice_extractor.text_layer.try_ocr_pdf",
            return_value=(None, None, "tesseract not found"),
        ):
            text, backend, needs = extract_text("scan.pdf", allow_ocr=True)
            assert not text.strip()
            assert needs is True
            assert "ocr_failed" in backend


def test_rules_engine_uses_ocr_text_same_path():
    """OCR text goes through classify/apply_format — no separate OCR format_id."""
    fake_ocr = "Bosch Home Comfort Supply\nInvoice Number: 9027451705\nTOTALS: 100.00\nPART NO\nQUANTITIES\n"
    with patch(
        "invoice_extractor.text_layer.extract_text",
        return_value=(fake_ocr, OCR_BACKEND, False),
    ):
        r = extract_invoice(Path("fake_scan.pdf"))
        d = r.to_dict()
        assert d["meta"]["text_backend"] == OCR_BACKEND
        assert d["meta"]["needs_ocr"] is False
        # May or may not match bhc depending on score; backend must stay ocr
        assert d["meta"]["format_id"] != "ocr_v1"
        assert "ocr" not in (d["meta"]["format_id"] or "")


@pytest.mark.skipif(not CASE7_INV.is_file(), reason="case7 invoice309.pdf missing")
@pytest.mark.skipif(not tesseract_available(), reason="tesseract not installed")
def test_case7_invoice_ocr_smoke():
    text, backend, needs = extract_layout_text(CASE7_INV)
    assert needs is True
    assert not text.strip()

    text2, backend2, needs2 = extract_text(CASE7_INV)
    assert needs2 is False
    assert backend2 == OCR_BACKEND
    assert "INVOICE" in text2.upper() or "NBT309" in text2.upper()

    r = extract_invoice(CASE7_INV)
    d = r.to_dict()
    assert d["meta"]["text_backend"] == OCR_BACKEND
    assert d["meta"]["needs_ocr"] is False
    # New vendor (Shanghai Nature) — no format yet is OK; path must not early-exit
    assert "empty text layer" not in (d["meta"].get("notes") or "")


@pytest.mark.skipif(not CASE7_PKL.is_file(), reason="case7 packing309.pdf missing")
@pytest.mark.skipif(not tesseract_available(), reason="tesseract not installed")
def test_case7_packing_ocr_smoke():
    text, backend, needs = extract_text(CASE7_PKL)
    assert needs is False
    assert backend == OCR_BACKEND
    assert len(text.strip()) > 20
