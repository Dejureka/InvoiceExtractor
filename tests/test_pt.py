from pathlib import Path

import pytest

from invoice_extractor.formats import pt_gloria_v1
from invoice_extractor.rules_engine import extract_invoice

FIXTURE_TXT = Path("/workspace/InvoiceExtractor/fixtures/pt_50656407_layout.txt")
FIXTURE_PDF = Path("/workspace/msg_extract/PT GmbH invoice_2026_07_09/50656407.PDF")


@pytest.mark.skipif(not FIXTURE_TXT.is_file(), reason="fixture missing")
def test_pt_invoice_no_from_layout_txt():
    text = FIXTURE_TXT.read_text(encoding="utf-8", errors="replace")
    r = pt_gloria_v1.extract_from_text(text, source_file="50656407", text_backend="fixture")
    assert r.header.invoice_no == "50656407"
    assert r.header.invoice_date == "2026-07-08"
    assert r.header.amount == pytest.approx(10091.68)
    assert r.header.currency == "USD"
    assert r.meta.format_id == "pt_gloria_v1"
    assert len(r.items) >= 1


@pytest.mark.skipif(not FIXTURE_PDF.is_file(), reason="PDF missing")
def test_pt_from_pdf():
    r = extract_invoice(FIXTURE_PDF)
    assert r.header.invoice_no == "50656407"
    assert r.meta.format_id == "pt_gloria_v1"
