"""hitachi_gls_v1 — BHC MEH6L040 conflict fix (inline ITEM# layout).

Four root causes, all generic (no case values in the rules):

1. Model ``P-AP90DNA*EX``: the inline-row PN pattern required an alphanumeric
   second character and had no ``*``, so the row after SUB TOTAL was dropped.
2. Packing TOTAL row carries only the PALLETS count; CARTONS and the printed
   ``N PACKAGES`` sum follow on later lines.
3. Description under the row shares text lines with the Marks & Numbers
   column (``MADE IN JAPAN`` / ``P80016921``); read it from the item column.
4. ``PSH-4,PC-ARFG2-T,P-AP90DNA*EX -ORIGIN: CHINA``: the ``*`` broke the
   per-model origin regex, so every line fell back to OTHERS/JP.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.formats.hitachi_gls_v1 import (
    _mixed_package_total,
    _origin_map,
    extract_from_text,
)
from invoice_extractor.rules_engine import extract_invoice

FX = Path(__file__).resolve().parents[1] / "fixtures" / "bhc_hitachi_MEH6L040"
PDF_NAME = "20261126_MEH6L040 (TY09,TY32, TY81, TY91, TY98).pdf"


@pytest.fixture(scope="module")
def meh6l040():
    text = (FX / "MEH6L040_layout.txt").read_text(encoding="utf-8")
    r = extract_invoice(Path("/nonexistent") / PDF_NAME, text=text, backend="pdftotext -layout", needs_ocr=False)
    d = r.to_dict()
    return d, hard_check(d)


@pytest.fixture(scope="module")
def gold():
    return json.loads((FX / "MEH6L040_gold.json").read_text(encoding="utf-8"))


def test_meh6l040_summary_matches_gold(meh6l040, gold):
    d, hard = meh6l040
    h, g = d["header"], gold["Summary"]
    assert d["meta"]["format_id"] == "hitachi_gls_v1"
    assert h["invoice_no"] == g["Invoice No."]
    assert h["total_pkg"] == g["Packages"]
    assert h["gross_weight_kg"] == g["G.W. (kgs)-Air DIM. (CBM)-Sea"]
    assert h["amount"] == g["Invoice Value"]
    assert h["item_line_count"] == g["LINE"]
    assert h["total_quantity"] == g["QTY"]
    assert h["currency"] == g["Invoice Currency"]
    # Same Incoterms form as the audited MEH6J044 / MEH6K018 rows.
    assert h["incoterm"] == "F.O.B. SHIMIZU, JAPAN"
    assert hard["verdict"] == "pass"


def test_meh6l040_lines_match_gold(meh6l040, gold):
    d, _ = meh6l040
    got = [
        {"PN": it["part_no"], "Des": it["description"], "Qty": it["qty"], "Unt": it["unit_price"],
         "Amt": it["amount"], "UoM": it["unit"], "Co": it["origin"]}
        for it in d["items"]
    ]
    assert got == gold["Lines"]
    assert sum(it["amount"] for it in d["items"]) == gold["Summary"]["Invoice Value"]


def test_origin_map_accepts_star_variant_models():
    per, other = _origin_map(
        "   PSH-4,PC-ARFG2-T,P-AP90DNA*EX -ORIGIN: CHINA\n   OTHERS -ORIGIN: JAPAN\n"
    )
    assert per == {"PSH-4": "CN", "PC-ARFG2-T": "CN", "P-AP90DNA*EX": "CN"}
    assert other == "JP"


def test_mixed_package_units_prefer_printed_packages_sum():
    after = "\n                  CARTONS\n                       19\n                   ----\n                       21 PACKAGES\n"
    assert _mixed_package_total(after, 2.0) == 21.0


def test_mixed_package_units_summed_without_packages_line():
    after = "\n                  CARTONS\n                        7\n\nSHGDL5301\n"
    assert _mixed_package_total(after, 3.0) == 10.0


def test_single_unit_total_unchanged():
    after = "\n                  CARTONS      =====  =====\n\n TOTAL :   16   4,815\n"
    assert _mixed_package_total(after, 16.0) == 16.0


_SYNTH = """\
                                                                  INVOICE
Invoice No.                                           Date
 BOSCH HOME COMFORT TAIWAN CO., LTD.          MEHZZ999                 JAN. 05, 2027
       Marks & Numbers                              Description                                Quantity     Unit Price                  Total Amount
                                   HITACHI AIR CONDITIONERS AND ACCESSORIES                               F.O.B. SHIMIZU , JAPAN
BOSCH-TW                           ITEM#
P11111111                          01    RAS-9.0ABC                                            3 PCS              10,000              30,000
MADE IN JAPAN
                                         OUTDOOR UNIT
CASE NO.1-3                        02    Q-XY12*EX                                             2 PCS               5,000              10,000
P22222222                                ACCESSORY: COVER
                                                                GRAND TOTAL:                   5 PCS                             J\u00a540,000
                                   Q-XY12*EX -ORIGIN: THAILAND
                                   OTHERS -ORIGIN: JAPAN
"""


def test_synthetic_star_model_marks_column_and_origin():
    r = extract_from_text(_SYNTH, source_file="x.pdf", text_backend="pdftotext -layout")
    rows = [(it.part_no, it.description, it.amount, it.origin) for it in r.items]
    assert rows == [
        ("RAS-9.0ABC", "OUTDOOR UNIT", 30000.0, "JP"),
        ("Q-XY12*EX", "ACCESSORY: COVER", 10000.0, "TH"),
    ]
