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


@pytest.mark.skipif(not FIXTURE_TXT.is_file(), reason="fixture missing")
def test_pt_gross_weight_not_net():
    """G.W. must be Packing Weight Gross (437.530), not tariff Net (340.394)."""
    text = FIXTURE_TXT.read_text(encoding="utf-8", errors="replace")
    r = pt_gloria_v1.extract_from_text(text, source_file="50656407", text_backend="fixture")
    assert r.header.gross_weight_kg == pytest.approx(437.530)
    # sanity: labeled Net must not win
    assert r.header.gross_weight_kg != pytest.approx(340.394)


def test_pt_gross_weight_packing_snippet():
    """Minimal packing-details snippet: prefer Gross Weight label / footer."""
    snippet = """
Tarif Code                                              Net Weight                         Value
total                                                   340.394 KG                10,091.68 USD
total:                                                 Net Weight:                    340.394 KG
                                                       Gross Weight:                    437.530 KG
Packing no.                                                                                                                                            Weight Net             Weight Gross                         Dimensions             Value of goods
total                                                                                                                                          ______________            ______________
                                                                                                                                                    340.394 kg                437.530 kg
"""
    r = pt_gloria_v1.extract_from_text(snippet, source_file="snippet", text_backend="fixture")
    assert r.header.gross_weight_kg == pytest.approx(437.530)


def test_pt_gross_weight_thousands_comma():
    """US thousands in Gross Weight (e.g. 50656462)."""
    snippet = """
total: Net Weight:   1,239.840 KG
Gross Weight:   1,319.840 KG
  1,239.840 kg   1,319.840 kg
"""
    r = pt_gloria_v1.extract_from_text(snippet, source_file="50656462", text_backend="fixture")
    assert r.header.gross_weight_kg == pytest.approx(1319.840)
