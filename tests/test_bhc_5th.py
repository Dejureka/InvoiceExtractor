"""BHC 5th batch (2026-10-05) FormatSOP regression.

Text fixtures in ``fixtures/bhc5/`` cover:

- ``bhc_vendor_ci_v1`` new profiles ``katata`` (PDF OCR + xlsx twin) and
  ``nisshinbo`` (OCR INV+PL)
- existing ``nidec_v1`` on VKT26075 (unchanged layout)
- ``tvl_hbl_v1`` vote fixes: SAY OCR ($1X→SIX / SAYTOTAL / marks C/NO.…/N
  PALLET), slash-row GW preferred when pkg matches, uncorroborated multi-pass
  GW → needs_gold
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.formats.bl import tvl_hbl_v1
from invoice_extractor.rules_engine import extract_invoice

FX = Path(__file__).resolve().parents[1] / "fixtures" / "bhc5"


def _t(name: str) -> str:
    return (FX / name).read_text(encoding="utf-8")


def _inv(fixture: str, filename: str, backend: str = "pdftotext -layout"):
    r = extract_invoice(
        Path("/nonexistent") / filename,
        text=_t(fixture),
        backend=backend,
        needs_ocr=False,
    )
    d = r.to_dict()
    return d, hard_check(d)


def test_katata_xlsx_twin():
    d, hard = _inv("c1_katata_xlsx.txt", "BSTW2609003 LCL  博世台湾.xlsx", "excel/openpyxl")
    h = d["header"]
    assert d["meta"]["format_id"] == "bhc_vendor_ci_v1"
    assert "profile=katata" in (d["meta"].get("notes") or "")
    assert h["invoice_no"] == "BSTW2609003"
    assert h["amount"] == pytest.approx(38806.7)
    assert len(d["items"]) == 8
    assert (h["total_pkg"], h["gross_weight_kg"]) == (6.0, 1195.5)
    assert h["incoterm"] == "FOB SHANGHAI"
    assert all(it["part_no"] for it in d["items"])
    assert all(it["hs_code"] == "8415909000" for it in d["items"])
    assert hard["verdict"] == "pass"


def test_katata_pdf_ocr():
    d, hard = _inv("c1_katata_pdf_ocr.txt", "BSTW2609003.pdf", "ocr/tesseract")
    h = d["header"]
    assert d["meta"]["format_id"] == "bhc_vendor_ci_v1"
    assert "profile=katata" in (d["meta"].get("notes") or "")
    assert h["invoice_no"] == "BSTW2609003"
    assert h["amount"] == pytest.approx(38806.7)
    assert len(d["items"]) == 8
    assert (h["total_pkg"], h["gross_weight_kg"]) == (6.0, 1195.5)
    assert hard["verdict"] == "pass"


def test_nidec_vkt26075_unchanged():
    d, hard = _inv("c2_nidec_pdf.txt", "BHC-TW_VKT26075_Z2609324.pdf")
    h = d["header"]
    assert d["meta"]["format_id"] == "nidec_v1"
    assert h["invoice_no"] == "VKT26075"
    assert h["amount"] == pytest.approx(89520.8)
    assert len(d["items"]) == 3
    assert (h["total_pkg"], h["gross_weight_kg"]) == (31.0, 13101.0)
    assert hard["verdict"] == "pass"


def test_nisshinbo_tawa_ocr():
    d, hard = _inv(
        "c3_nisshinbo_ocr.txt",
        "TAWA-26024(260921)Invoice & Packinglist.pdf",
        "ocr/tesseract",
    )
    h = d["header"]
    assert d["meta"]["format_id"] == "bhc_vendor_ci_v1"
    assert "profile=nisshinbo" in (d["meta"].get("notes") or "")
    assert h["invoice_no"] == "TAWA-26024"
    assert h["amount"] == pytest.approx(24240.0)
    assert len(d["items"]) == 1
    assert d["items"][0]["part_no"] == "2GF34793A"
    assert (h["total_pkg"], h["gross_weight_kg"]) == (240.0, 4850.88)
    assert h["incoterm"] == "FOB SHANGHAI"
    assert hard["verdict"] == "pass"


def test_tvl_say_six_and_marks_pkg():
    """Case 1 HBL: OCR face '18 PALLETS' / 1498.5 but SAY SIX (6) + C/NO.…/6 PALLET."""
    text = _t("c1_tvl_hbl_ocr.txt")
    votes = tvl_hbl_v1._read_votes(text)
    say_vals = {v for _, v in votes["say"]}
    assert 6.0 in say_vals


def test_tvl_case2_slash_gw_in_votes():
    """Case 2: slash 31PALLETS/13101 kept even when face reads 13104."""
    text = _t("c2_tvl_hbl_ocr.txt")
    votes = tvl_hbl_v1._read_votes(text)
    assert votes["rows"]
    assert any(abs((w or 0) - 13101.0) < 0.01 for _, w in votes["rows"])


def test_nidec_does_not_steal_tvl_bl():
    from invoice_extractor.formats import nidec_v1

    text = _t("c2_tvl_hbl_ocr.txt")
    assert nidec_v1.match_score(text, "20260924163130-0001.pdf") < 0.3
