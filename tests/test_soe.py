"""SOE Robert Bosch GmbH invoice + KWE/Maersk HAWB tests."""

from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.formats import bhc_my_hub_v1, soe_rb_gmbh_v1
from invoice_extractor.formats.bl import kwe_air_waybill_v1, maersk_air_waybill_v1
from invoice_extractor.checker_bl import hard_check_bl
from invoice_extractor.rules_engine import classify

FIXTURE_INV = Path(__file__).resolve().parents[1] / "fixtures" / "soe_7077533916_layout.txt"
FIXTURE_MULTI = Path(__file__).resolve().parents[1] / "fixtures" / "soe_7077530221_layout.txt"
FIXTURE_KWE = Path(__file__).resolve().parents[1] / "fixtures" / "soe_kwe_hawb_layout.txt"
FIXTURE_MAERSK = Path(__file__).resolve().parents[1] / "fixtures" / "soe_maersk_hawb_layout.txt"


@pytest.mark.skipif(not FIXTURE_INV.is_file(), reason="fixture missing")
def test_soe_single_line_extract():
    text = FIXTURE_INV.read_text(encoding="utf-8", errors="replace")
    r = soe_rb_gmbh_v1.extract("7077533916.pdf", text, "fixture", False)
    assert r.meta.format_id == "soe_rb_gmbh_v1"
    assert r.header.invoice_no == "7077533916"
    assert r.header.amount == pytest.approx(159.98)
    assert r.header.currency == "EUR"
    assert r.header.gross_weight_kg == pytest.approx(26.628)
    assert r.header.total_pkg == pytest.approx(1.0)
    assert "FCA" in (r.header.incoterm or "")
    assert len(r.items) == 1
    it = r.items[0]
    assert it.part_no == "0265.299.799-V5A"
    assert it.qty == pytest.approx(3.0)
    assert it.hs_code == "90328100"
    assert it.origin == "TH"
    # Price unit 100 → unit_price = 5332.55/100
    assert it.unit_price == pytest.approx(53.3255)
    data = r.to_dict()
    data["meta"]["labeled_amount"] = r.meta.labeled_amount
    data["meta"]["labeled_amount_label"] = r.meta.labeled_amount_label
    assert hard_check(data)["verdict"] == "pass"


@pytest.mark.skipif(not FIXTURE_MULTI.is_file(), reason="fixture missing")
def test_soe_two_lines_sum_amount():
    text = FIXTURE_MULTI.read_text(encoding="utf-8", errors="replace")
    r = soe_rb_gmbh_v1.extract("7077530221.pdf", text, "fixture", False)
    assert r.header.invoice_no == "7077530221"
    assert r.header.amount == pytest.approx(2855.90)
    assert len(r.items) == 2
    assert sum(it.amount or 0 for it in r.items) == pytest.approx(2855.90)
    assert r.header.total_pkg == pytest.approx(2.0)
    assert r.header.gross_weight_kg == pytest.approx(65.5)
    data = r.to_dict()
    data["meta"]["labeled_amount"] = r.meta.labeled_amount
    data["meta"]["labeled_amount_label"] = r.meta.labeled_amount_label
    assert hard_check(data)["verdict"] == "pass"


@pytest.mark.skipif(not FIXTURE_INV.is_file(), reason="fixture missing")
def test_soe_not_bhc_and_classifies():
    text = FIXTURE_INV.read_text(encoding="utf-8", errors="replace")
    assert soe_rb_gmbh_v1.match_score(text, "INV_PL_7077533916.pdf") >= 0.8
    assert bhc_my_hub_v1.match_score(text, "INV_PL_7077533916.pdf") < 0.3
    fid, sc = classify(text, "INV_PL_7077533916.pdf")
    assert fid == "soe_rb_gmbh_v1"
    assert sc >= 0.8


@pytest.mark.skipif(not FIXTURE_KWE.is_file(), reason="fixture missing")
def test_kwe_hawb():
    text = FIXTURE_KWE.read_text(encoding="utf-8", errors="replace")
    assert kwe_air_waybill_v1.match_score(text, "122019555195-HAWC.pdf") >= 0.8
    r = kwe_air_waybill_v1.extract("122019555195-HAWC.pdf", text, "fixture", False)
    assert r.header.bl_no == "1220-19555195"
    assert r.header.packages == pytest.approx(1.0)
    assert r.header.gross_weight_kg == pytest.approx(496.0)
    assert r.header.invoice_refs == "7077559620"
    assert hard_check_bl(r.to_dict())["verdict"] == "pass"


@pytest.mark.skipif(not FIXTURE_MAERSK.is_file(), reason="fixture missing")
def test_maersk_hawb():
    text = FIXTURE_MAERSK.read_text(encoding="utf-8", errors="replace")
    assert maersk_air_waybill_v1.match_score(text, "HAWB No_ QU100002136.pdf") >= 0.8
    r = maersk_air_waybill_v1.extract("hawb.pdf", text, "fixture", False)
    assert r.header.bl_no == "QU100002136"
    assert r.header.packages == pytest.approx(2.0)
    assert r.header.gross_weight_kg == pytest.approx(294.5)
    assert hard_check_bl(r.to_dict())["verdict"] == "pass"


def test_soe_false_extract_fails_hard():
    """Incomplete extract (wrong amount / missing HS) must conflict."""
    bad = {
        "header": {"invoice_no": "7077533916", "amount": 159.98, "currency": "EUR"},
        "items": [
            {
                "part_no": "0265.299.799-V5A",
                "qty": 3,
                "unit_price": 53.3255,
                "amount": 50.0,  # wrong
                "hs_code": "90328100",
                "currency": "EUR",
            }
        ],
        "meta": {
            "format_id": "soe_rb_gmbh_v1",
            "labeled_amount": 159.98,
            "labeled_amount_label": "Invoice amount",
        },
    }
    assert hard_check(bad)["verdict"] == "conflict"
    bad2 = {
        "header": {"invoice_no": "7077533916", "amount": 159.98},
        "items": [
            {
                "part_no": "x",
                "qty": 3,
                "unit_price": 53.3255,
                "amount": 159.98,
                "hs_code": "",
                "currency": "EUR",
            }
        ],
        "meta": {
            "format_id": "soe_rb_gmbh_v1",
            "labeled_amount": 159.98,
            "labeled_amount_label": "Invoice amount",
        },
    }
    assert hard_check(bad2)["verdict"] == "conflict"
