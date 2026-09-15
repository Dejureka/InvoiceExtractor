from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.formats import pt_dremel_head3_v1, pt_dremel_head5_v1, pt_gloria_v1
from invoice_extractor.rules_engine import classify, extract_invoice

TXT = Path("/workspace/InvoiceExtractor/out/pt_dremel/txt")
PDF = Path("/home/box/Downloads/PT_dremel")

H3_TXT = TXT / "40-D-25PT-412_RB TAIWAN P13 INVOICE 5064641 DHL AWB#5604076376.txt"
H5_TXT = TXT / "90-DSV-26PT-103_REVISED INVOICE, PPT INVOICE SHIP TO RB TAIWAN DOC#5005360.txt"
PAGEBREAK_TXT = TXT / "90-DSV-25PT-459_RB TAIWAN P13 INVOICE 5061330 BKG#83395775 SEFL 3521 5071-8.txt"


@pytest.mark.skipif(not H3_TXT.is_file(), reason="head3 fixture missing")
def test_head3_extract_and_not_gloria():
    text = H3_TXT.read_text(encoding="utf-8", errors="replace")
    assert pt_dremel_head3_v1.match_score(text, H3_TXT.name) >= 0.7
    assert pt_gloria_v1.match_score(text, H3_TXT.name) < 0.3
    fid, score = classify(text, H3_TXT.name)
    assert fid == "pt_dremel_head3_v1"
    assert score >= 0.7
    r = pt_dremel_head3_v1.extract_from_text(text, source_file=H3_TXT.name)
    assert r.header.invoice_no == "3415154586"
    assert r.header.amount == pytest.approx(1384.14)
    assert r.header.currency == "USD"
    assert len(r.items) == 7
    assert all(it.hs_code for it in r.items)
    hc = hard_check(r.to_dict())
    assert hc["verdict"] == "pass"


@pytest.mark.skipif(not H5_TXT.is_file(), reason="head5 fixture missing")
def test_head5_extract_gw_gross():
    text = H5_TXT.read_text(encoding="utf-8", errors="replace")
    assert pt_dremel_head5_v1.match_score(text, H5_TXT.name) >= 0.7
    assert pt_dremel_head3_v1.match_score(text, H5_TXT.name) < 0.4
    r = pt_dremel_head5_v1.extract_from_text(text, source_file=H5_TXT.name)
    assert r.header.invoice_no == "580020154"
    assert r.header.amount == pytest.approx(15723.36)
    assert r.header.gross_weight_kg == pytest.approx(604.0)
    assert r.header.gross_weight_kg != pytest.approx(541.888)  # not Net
    assert len(r.items) == 3
    assert all(it.hs_code for it in r.items)
    hc = hard_check(r.to_dict())
    assert hc["verdict"] == "pass"


@pytest.mark.skipif(not PAGEBREAK_TXT.is_file(), reason="pagebreak fixture missing")
def test_head3_pagebreak_hs():
    text = PAGEBREAK_TXT.read_text(encoding="utf-8", errors="replace")
    r = pt_dremel_head3_v1.extract_from_text(text, source_file=PAGEBREAK_TXT.name)
    assert len(r.items) == 15
    assert all(it.hs_code for it in r.items)
    # page-break line 2.615.010.5AE
    hit = [it for it in r.items if it.part_no == "2.615.010.5AE"]
    assert hit and hit[0].hs_code == "8207907585"


@pytest.mark.skipif(not PDF.is_dir(), reason="PDF dir missing")
def test_batch_all_pass():
    pdfs = sorted(PDF.glob("*.pdf"))
    assert len(pdfs) == 16
    for pdf in pdfs:
        r = extract_invoice(pdf)
        assert r.meta.format_id in {"pt_dremel_head3_v1", "pt_dremel_head5_v1"}
        hc = hard_check(r.to_dict())
        assert hc["verdict"] == "pass", (pdf.name, hc)
