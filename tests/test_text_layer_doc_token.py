"""OCR-vs-layer choice uses document-number shapes, not vendor prefixes (synthetic)."""
from __future__ import annotations

import pytest

from invoice_extractor.text_layer import ocr_text_looks_more_reliable

OCR = "PACKING LIST\nInvoice {no}\n(TOTAL: 3 PALLETS ONLY)\n"


@pytest.mark.parametrize("no", ["USDI4105369", "9027451705", "9028123456", "AB1234567", "OK20260921"])
def test_shared_number_prefers_ocr(no):
    layer = f"PACKING LIST\nInvoice {no}\nstale body without totals\n"
    assert ocr_text_looks_more_reliable(layer, OCR.format(no=no))


def test_different_document_keeps_layer():
    layer = "PACKING LIST\nInvoice 9028000001\nstale body\n"
    assert not ocr_text_looks_more_reliable(layer, OCR.format(no="9028999999"))


def test_layer_with_its_own_pallet_total_keeps_layer():
    layer = "Invoice 9028123456\nTOTAL: 3 PALLETS\n"
    assert not ocr_text_looks_more_reliable(layer, OCR.format(no="9028123456"))


@pytest.mark.private_samples("unit/ocr_text/bhc3_case8_PACKING_LIST_BOSCH.tesseract5.txt",
                             "regression/cov8/bhc3_case8/PACKING LIST (BOSCH).pdf")
def test_real_hitachi_pkl_still_prefers_ocr():
    import samples
    from invoice_extractor.text_layer import extract_layout_text

    layer, _, _ = extract_layout_text(samples.path("regression/cov8/bhc3_case8/PACKING LIST (BOSCH).pdf"))
    ocr = samples.path("unit/ocr_text/bhc3_case8_PACKING_LIST_BOSCH.tesseract5.txt").read_text(encoding="utf-8")
    assert ocr_text_looks_more_reliable(layer, ocr)
