from pathlib import Path

import pytest

from invoice_extractor.formats import bitzer_v1
from invoice_extractor.rules_engine import extract_invoice

FIXTURE_TXT = Path("/workspace/InvoiceExtractor/fixtures/bitzer_3000214469.txt")
FIXTURE_PDF_CANDIDATES = [
    Path(
        "/home/box/Downloads/BHC_invoice_samples/"
        "3000214469_TW_708822_BOSCH_HOME_COMFORT_TAIWAN_CO_LTD__Versanddokument.pdf"
    ),
    Path(
        "/home/box/Downloads/BHC_invoice_samples_mega/"
        "3000214469_TW_708822_BOSCH_HOME_COMFORT_TAIWAN_CO_LTD__Versanddokument.pdf"
    ),
]
FIXTURE_PDF = next((p for p in FIXTURE_PDF_CANDIDATES if p.is_file()), FIXTURE_PDF_CANDIDATES[0])

EXPECTED_HEADER = {
    "invoice_no": "200167553",
    "invoice_date": "2025-12-04",
    "total_pkg": 7.0,
    "gross_weight_kg": 6052.4,
    "currency": "EUR",
    "item_line_count": 5,
    "total_quantity": 7.0,
    "amount": 37041.41,
}


@pytest.mark.skipif(not FIXTURE_TXT.is_file(), reason="fixture missing")
def test_bitzer_header_from_txt():
    text = FIXTURE_TXT.read_text(encoding="utf-8", errors="replace")
    r = bitzer_v1.extract_from_text(text, source_file=str(FIXTURE_TXT), text_backend="fixture")
    h = r.header.to_dict()
    for k, want in EXPECTED_HEADER.items():
        got = h[k]
        if isinstance(want, float):
            assert got == pytest.approx(want), f"{k}: {got} != {want}"
        else:
            assert got == want, f"{k}: {got} != {want}"
    assert r.meta.format_id == "bitzer_v1"
    assert len(r.items) == 5
    assert r.header.origin == "DE"
    assert r.header.hs_code == "84143081"
    assert all(it.origin == "DE" for it in r.items)
    assert all(it.hs_code == "84143081" for it in r.items)


@pytest.mark.skipif(not FIXTURE_PDF.is_file(), reason="PDF missing")
def test_bitzer_from_pdf():
    r = extract_invoice(FIXTURE_PDF)
    assert r.header.invoice_no == "200167553"
    assert r.header.amount == pytest.approx(37041.41)
    assert r.meta.format_id == "bitzer_v1"
