"""MA AK Billing: Gross HU Weight parse + shipment_first HU dedupe (AK00074096–098)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.formats.ma_ak_billing_v1 import extract_from_text
from invoice_extractor.formats.ma_common import parse_ak_packages, parse_ak_units
from invoice_extractor.pairing import dedupe_shared_packing_units

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

# Hand-computed from pdftotext -layout Marking lines (unique 18-digit HU + Gross HU Weight).
GOLD = {
    "AK00074096": (30.0, 7653.0),
    "AK00074097": (10.0, 1137.28),
    "AK00074098": (10.0, 1137.28),
}
SHIP_PKG, SHIP_GW = 40.0, 8790.28
SHARED = {
    "406702140321949730",
    "406702140322506154",
    "406702140322528170",
    "406702140323114235",
    "406702140323149664",
    "406702140323149916",
    "406702140323150264",
    "406702140323154286",
    "406702140323179739",
    "406702140323180025",
}


def _text(inv: str) -> str:
    return (FIXTURES / f"ma_ak_{inv}_layout.txt").read_text()


def test_parse_ak_gross_hu_weight_and_continuation_without_rb():
    """Only the first HU has the RB label; later 18-digit ids still count."""
    text = """
Marking
RB        406702140321949730                    Dummy Pack. Mat. for Carton                          26x25x8CM                  Gross HU Weight 1.280       KG
                                                                                                                                Net HU Weight 1.120         KG
          406702140322506154                    Dummy Pack. Mat. for PALLET                          120x100x100CM              Gross HU Weight 310.000     KG
                                                POS-no                                               10                         Net Val         12,528      TWD
          406702140322528170                    Dummy Pack. Mat. for PALLET                          120x80x100CM               Gross HU Weight 102.000     KG
"""
    units = parse_ak_units(text)
    assert list(units) == [
        "406702140321949730",
        "406702140322506154",
        "406702140322528170",
    ]
    assert units["406702140321949730"] == 1.28
    assert units["406702140322506154"] == 310.0
    assert parse_ak_packages(text) == (3.0, 413.28)


def test_parse_ak_first_occurrence_wins_within_file():
    text = """
Marking
RB        406702140321949730  Dummy Pack. Mat. for Carton  26x25x8CM  Gross HU Weight 1.280  KG
          406702140321949730  Dummy Pack. Mat. for Carton  26x25x8CM  Gross HU Weight 9.999  KG
"""
    assert parse_ak_packages(text) == (1.0, 1.28)


def test_parse_ak_does_not_concat_second_segment():
    """18-digit HU must not swallow a dimension or weight token as a second key part."""
    text = """
Marking
RB        406702140321949730                    Dummy Pack. Mat. for Carton                          26x25x8CM                  Gross HU Weight 1.280       KG
"""
    units = parse_ak_units(text)
    assert list(units) == ["406702140321949730"]


def test_parse_ak_page_break_keeps_gross_on_hu_line():
    """Gross already on the HU line; Net / footer on the next page must not drop the HU."""
    text = """
Marking
          406702140323114235                    Dummy Pack. Mat. for PALLET                          120x80x100CM               Gross HU Weight 400.000     KG
                                             Laura.Precup-Muresan@ro.bosch.com
                                                                                                                                  Net HU Weight 375.000    KG
                                                  POS-no                                              10                          Net Val         33,408   TWD
          406702140323149664                      Dummy Pack. Mat. for PALLET                         120x80x100CM                Gross HU Weight 56.000   KG
"""
    units = parse_ak_units(text)
    assert units["406702140323114235"] == 400.0
    assert units["406702140323149664"] == 56.0
    assert parse_ak_packages(text) == (2.0, 456.0)


def test_parse_ak_pos_no_and_net_val_are_not_packages():
    text = """
Marking
RB        406702140321238308                    Dummy Pack. Mat. for Carton                          66x46x33CM                  Gross HU Weight 17.800    KG
                                                POS-no                                               70                          Net Val         10,611    TWD
                                                POS-no                                               80                          Net Val         1,730     TWD
"""
    units = parse_ak_units(text)
    assert list(units) == ["406702140321238308"]
    assert units["406702140321238308"] == 17.8


def test_parse_ak_old_gross_wording_still_works():
    """Earlier AK invoices printed 'Gross 5.000 KG' without 'HU Weight'."""
    text = """
Marking
RB        406702140305951117                    Dummy Pack. Mat. for Carton                          42x33x22CM                         Gross          5.000        KG
          406702140306057023                    Dummy Pack. Mat. for PALLET                          120x80x100CM                       Gross          333.000      KG
"""
    assert parse_ak_packages(text) == (2.0, 338.0)


@pytest.mark.parametrize("inv", ["AK00074096", "AK00074097", "AK00074098"])
def test_fixtures_per_invoice_pkg_gw(inv):
    text = _text(inv)
    pkg, gw = GOLD[inv]
    assert parse_ak_packages(text) == (pkg, gw)
    res = extract_from_text(text, source_file=f"/ship/{inv}.PDF")
    assert res.meta.format_id == "ma_ak_billing_v1"
    assert res.header.invoice_no == inv
    assert res.header.total_pkg == pkg
    assert res.header.gross_weight_kg == gw
    assert res.meta.packing_units and len(res.meta.packing_units) == int(pkg)
    assert abs(sum(res.meta.packing_units.values()) - gw) <= 0.001
    assert res.items and all(it.hs_code for it in res.items)
    assert hard_check(res.to_dict())["verdict"] == "pass"


def test_shipment_first_puts_union_on_first_invoice():
    ds = []
    for inv in ("AK00074096", "AK00074097", "AK00074098"):
        res = extract_from_text(_text(inv), source_file=f"/ship/{inv}.PDF")
        ds.append(res.to_dict())
    # 097 and 098 share the same 10 HUs; 096's 30 HUs are disjoint.
    assert set(ds[1]["meta"]["packing_units"]) == SHARED
    assert set(ds[2]["meta"]["packing_units"]) == SHARED
    assert set(ds[0]["meta"]["packing_units"]).isdisjoint(SHARED)
    notes = dedupe_shared_packing_units(ds)
    assert notes
    by = {d["header"]["invoice_no"]: d for d in ds}
    assert by["AK00074096"]["header"]["total_pkg"] == SHIP_PKG
    assert by["AK00074096"]["header"]["gross_weight_kg"] == SHIP_GW
    assert by["AK00074097"]["header"]["total_pkg"] == 0.0
    assert by["AK00074097"]["header"]["gross_weight_kg"] == 0.0
    assert by["AK00074098"]["header"]["total_pkg"] == 0.0
    assert by["AK00074098"]["header"]["gross_weight_kg"] == 0.0
    assert "shipment pkg/GW (deduped) 40 / 8790.28" in (by["AK00074096"]["header"]["summary_note"] or "")
    assert "on AK00074096" in (by["AK00074097"]["header"]["summary_note"] or "")
    for d in ds:
        assert hard_check(d)["verdict"] == "pass"
