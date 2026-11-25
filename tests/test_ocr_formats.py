"""FormatSOP on OCR scan samples (BHC case2 / case7) + TVL HBL."""

from __future__ import annotations

from pathlib import Path

import pytest

import samples
from conftest import require_samples

from invoice_extractor.bl_rules_engine import extract_bl
from invoice_extractor.checker import hard_check
from invoice_extractor.ocr import tesseract_available
from invoice_extractor.pairing import parse_packing_pkg_gw
from invoice_extractor.rules_engine import extract_invoice
from invoice_extractor.text_layer import extract_text

CASE2 = samples.path("unit/bhc_cases_round/case2/(JCH26-08M1) Invoice, PL.pdf")
CASE7_INV = samples.path("unit/bhc_cases_round/case7/invoice309.pdf")
CASE7_BL = samples.path("unit/bhc_cases_round/case7/20260903091515-0001.pdf")
CASE8_BL = samples.path("unit/bhc_cases_round/case8/20260904232648-0001.pdf")
CASE4_PKL = samples.path("unit/bhc_cases_round/case4/PKL_TA2608B2-3253,TA2608B3254.pdf")

need_tess = pytest.mark.skipif(not tesseract_available(), reason="tesseract missing")
need_case2 = pytest.mark.private_samples("unit/bhc_cases_round/case2/(JCH26-08M1) Invoice, PL.pdf")
need_case7 = pytest.mark.private_samples("unit/bhc_cases_round/case7/invoice309.pdf")


@need_tess
@need_case7
def test_shanghai_nature_ocr_case7():
    r = extract_invoice(CASE7_INV)
    d = r.to_dict()
    assert d["meta"]["text_backend"] == "ocr/tesseract"
    assert d["meta"]["format_id"] == "shanghai_nature_v1"
    assert d["header"]["invoice_no"] == "NBT309"
    assert d["header"]["amount"] == pytest.approx(7478.1)
    assert len(d["items"]) == 6
    assert hard_check(d)["verdict"] == "pass"


@need_tess
@need_case2
def test_marubeni_ocr_case2():
    r = extract_invoice(CASE2)
    d = r.to_dict()
    assert d["meta"]["text_backend"] == "ocr/tesseract"
    assert d["meta"]["format_id"] == "marubeni_tetsugen_v1"
    assert d["header"]["invoice_no"] == "JCH26-08M1"
    assert d["header"]["amount"] == pytest.approx(67930.24)
    assert d["header"]["total_pkg"] == 5
    assert d["header"]["gross_weight_kg"] == pytest.approx(3560.0)
    assert len(d["items"]) == 2
    assert hard_check(d)["verdict"] == "pass"


@need_tess
@pytest.mark.private_samples("unit/bhc_cases_round/case7/20260903091515-0001.pdf")
def test_tvl_hbl_ocr_case7():
    d = extract_bl(CASE7_BL).to_dict()
    assert d["meta"]["format_id"] == "tvl_hbl_v1"
    assert d["meta"]["text_backend"] == "ocr/tesseract"
    assert d["header"]["bl_no"] == "SHAKEL26970898"
    assert d["header"]["packages"] == 1
    assert d["header"]["gross_weight_kg"] == pytest.approx(231.0)


@need_tess
@pytest.mark.private_samples("unit/bhc_cases_round/case8/20260904232648-0001.pdf")
def test_tvl_hbl_ocr_case8():
    d = extract_bl(CASE8_BL).to_dict()
    assert d["meta"]["format_id"] == "tvl_hbl_v1"
    assert d["header"]["bl_no"] == "SHAKEL26770270"
    # Prefer face CARTONS over Say-Total 1×20GP (FormatSOP BHC 3rd round-2).
    assert d["header"]["packages"] == 326
    assert d["header"]["package_unit"] == "CARTONS"
    assert d["header"]["gross_weight_kg"] == pytest.approx(3469.5)


@need_tess
@pytest.mark.private_samples("unit/bhc_cases_round/case4/PKL_TA2608B2-3253,TA2608B3254.pdf")
def test_bhc_thailand_pkl_ocr_pkg_gw():
    text, backend, needs = extract_text(CASE4_PKL)
    assert backend == "ocr/tesseract"
    assert not needs
    pkg, gw = parse_packing_pkg_gw(text)
    assert pkg == 39
    assert gw == pytest.approx(6389.94)
