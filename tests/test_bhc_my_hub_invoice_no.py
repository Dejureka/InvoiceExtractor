"""bhc_my_hub_v1 invoice-number extraction (902x family, wide value-row window).

The pdftotext -layout value row puts the consignee name before the invoice
number. The old ``\\S[^\\n]{0,80}?`` window was 84 characters on every
audited MY-HUB sample, so the primary regex never matched; 9027… invoices
only worked because of a 9027-only fallback. 9028… numbers were missed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.formats.bhc_my_hub_v1 import _invoice_no, match_score
from invoice_extractor.rules_engine import extract_invoice

FX = Path(__file__).resolve().parents[1] / "fixtures" / "bhc_my_hub_9028"
FX6 = Path(__file__).resolve().parents[1] / "fixtures" / "bhc6"
PDF = "pdftotext -layout"

# Value-row padding longer than the old 80-char cap, with a non-9027 number so
# a prefix fallback cannot hide a window regression.
_WIDE_ROW = (
    " Consignee:                                                                          "
    "Invoice Number:           Invoice Date:                 Page:\n"
    "   Bosch Home Comfort Taiwan Co., Ltd."
    + (" " * 60)
    + "9030123456                25.11.2026                 1/1\n"
    "   P10062527   Delivery 10226901\n"
)

_STACKED = (
    "Invoice Number:\n"
    "9030123456\n"
    "Invoice Date:\n"
    "25.11.2026\n"
    "Page:\n"
    "1 / 1\n"
    "Supplier Reference:  BHCWHYTW2611005\n"
    "PO NO  LINE NO\n"
    "P10062527    60\n"
)


def _t(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _inv(text: str, filename: str, backend: str = PDF):
    r = extract_invoice(
        Path("/nonexistent") / filename,
        text=text,
        backend=backend,
        needs_ocr=False,
    )
    d = r.to_dict()
    return d, hard_check(d)


@pytest.mark.parametrize(
    "fixture,filename,inv_no,amount,lines,qty,date",
    [
        (
            "9028194267_layout.txt",
            "BHCWHYTW2611005_INV_9028194267.PDF",
            "9028194267",
            17140.8,
            2,
            480.0,
            "2026-11-25",
        ),
        (
            "9028111779_layout.txt",
            "BHCWHYTW2611001_INV_9028111779.PDF",
            "9028111779",
            219865.3,
            29,
            11211.0,
            "2026-11-12",
        ),
    ],
)
def test_my_hub_9028_invoices(fixture, filename, inv_no, amount, lines, qty, date):
    d, hard = _inv(_t(FX / fixture), filename)
    h = d["header"]
    assert d["meta"]["format_id"] == "bhc_my_hub_v1"
    assert h["invoice_no"] == inv_no
    assert h["invoice_date"] == date
    assert h["amount"] == pytest.approx(amount)
    assert len(d["items"]) == lines
    assert h["total_quantity"] == pytest.approx(qty)
    assert hard["verdict"] == "pass"


def test_value_row_window_wider_than_80_without_9027_fallback():
    # 60 spaces after "Ltd." plus the company name is well over 80 chars
    # from the first non-space character to the invoice number.
    assert _invoice_no(_WIDE_ROW) == "9030123456"
    d, hard = _inv(_WIDE_ROW + "\nTOTALS: 1.00\nPART NO\nQUANTITIES\nBosch Home Comfort Supply\nMY-HUB FINANCE\n", "INV_9030123456.PDF")
    assert d["meta"]["format_id"] == "bhc_my_hub_v1"
    assert d["header"]["invoice_no"] == "9030123456"


def test_stacked_label_value_and_ignores_po_and_delivery_refs():
    assert _invoice_no(_STACKED) == "9030123456"
    # PO / delivery / supplier-ref tokens must not win over the labeled number
    assert "P10062527" not in (_invoice_no(_STACKED) or "")
    assert "10226901" not in (_invoice_no(_WIDE_ROW) or "")
    assert _invoice_no(_WIDE_ROW) != "10226901"


def test_existing_9027_fixture_still_extracts():
    text = _t(FX6 / "c4_my_hub_inv.txt")
    assert _invoice_no(text) == "9027850165"
    d, hard = _inv(text, "10226901_INV_9027850165.PDF")
    assert d["meta"]["format_id"] == "bhc_my_hub_v1"
    assert d["header"]["invoice_no"] == "9027850165"
    assert hard["verdict"] == "pass"


def test_filename_score_accepts_9028_prefix():
    text = "Bosch Home Comfort Supply\nMY-HUB FINANCE\nTOTALS:\nInvoice Number:\nPART NO\nQUANTITIES\n"
    # 9028 filename without BHCWHY / TA2608 / 9027 tokens
    assert match_score(text, "INV_9028194267.PDF") >= 0.3
    assert match_score(text, "BHCWHYTW2611005_INV_9028194267.PDF") >= 0.3
    assert match_score(text, "TA2610B2_INV_9027972815.pdf") >= 0.3
