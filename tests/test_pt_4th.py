"""PT 4th batch (2026-09-26) regression: pt_gloria_v1 extended.

New samples: 40-D-26PT-404 (50664923), 90-C-26PT-405 (50654372 / 50654373).
Edge fixtures from the batch: 50663231 (packing row 1 vs total 12),
50664217 (mixed 8/10-digit HS), 50665811 (Slip sheet packing type).
"""

from __future__ import annotations

import gzip
import re
from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.formats import pt_gloria_v1
from invoice_extractor.rules_engine import classify

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def _text(name: str) -> str:
    p = FIX / name
    if p.suffix == ".gz":
        return gzip.decompress(p.read_bytes()).decode("utf-8", errors="replace")
    return p.read_text(encoding="utf-8", errors="replace")


def _run(name: str, stem: str):
    text = _text(name)
    r = pt_gloria_v1.extract_from_text(text, source_file=stem, text_backend="fixture")
    d = r.to_dict()
    return text, r, d


CASES = [
    # fixture, stem, inv, date, amount, gw, pkg, lines, qty, origins
    ("pt4_50664923_layout.txt", "40-D-26PT-404_50664923", "50664923", "2026-08-31",
     1116.60, 15.100, 3, 5, 88, {"CN"}),
    ("pt4_50654373_layout.txt", "90-C-26PT-405_50654373", "50654373", "2026-06-26",
     1456.00, 65.000, 1, 1, 800, {"CN"}),
    ("pt4_50654372_layout.txt.gz", "90-C-26PT-405_50654372", "50654372", "2026-06-26",
     52165.90, 2712.860, 30, 261, 7116, None),
    ("pt4_50663231_layout.txt", "90-S-26PT-409_50663231", "50663231", "2026-08-19",
     14918.40, 4100.000, 12, 4, 20160, {"CN"}),
    ("pt4_50664217_layout.txt", "90-S-26PT-418_50664217", "50664217", "2026-08-26",
     41674.97, 1664.900, 11, 11, 957, {"MY"}),
    ("pt4_50665811_layout.txt", "90-S-26PT-419_50665811", "50665811", "2026-09-04",
     2575.68, 82.336, 1, 1, 48, {"CN"}),
]


@pytest.mark.parametrize("fx,stem,inv,date,amt,gw,pkg,nlines,qty,origins", CASES)
def test_pt4_header_lines_and_hard_check(fx, stem, inv, date, amt, gw, pkg, nlines, qty, origins):
    if not (FIX / fx).is_file():
        pytest.skip("fixture missing")
    text, r, d = _run(fx, stem)
    fid, _score = classify(text, stem + ".pdf")
    assert fid == "pt_gloria_v1"
    h = r.header
    assert h.invoice_no == inv
    assert h.invoice_date == date
    assert h.currency == "USD"
    assert h.amount == pytest.approx(amt)
    assert h.gross_weight_kg == pytest.approx(gw)
    assert h.total_pkg == pytest.approx(pkg)
    assert len(r.items) == nlines
    assert h.total_quantity == pytest.approx(qty)
    assert sum(i.amount for i in r.items) == pytest.approx(amt, abs=0.05)
    # PT strict: every line has an 8/10-digit HS + origin
    for it in r.items:
        assert it.hs_code and re.fullmatch(r"\d{8}|\d{10}", it.hs_code), it
        assert it.origin and re.fullmatch(r"[A-Z]{2}", it.origin), it
    if origins is not None:
        assert {i.origin for i in r.items} == origins
    assert hard_check(d)["verdict"] == "pass"


def test_pt4_50654372_multi_origin_and_shipping_units():
    fx = "pt4_50654372_layout.txt.gz"
    if not (FIX / fx).is_file():
        pytest.skip("fixture missing")
    text, r, _ = _run(fx, "90-C-26PT-405_50654372")
    assert len({m for m in re.findall(r"Shipping unit (\d+)", text)}) == 30
    origins = {i.origin for i in r.items}
    assert {"IN", "CN", "DE", "US", "TW", "HU"} <= origins
    first = r.items[0]
    assert (first.part_no, first.origin, first.hs_code) == ("0.603.B05.200", "IN", "76169990")
    assert r.meta.notes is None  # consistent doc → no soft notes


def test_pt4_soft_note_packing_rows_vs_total_50663231():
    """Vendor inconsistency: 1 packing row (qty 1) but 'total : 12' → keep 12, soft note."""
    fx = "pt4_50663231_layout.txt"
    if not (FIX / fx).is_file():
        pytest.skip("fixture missing")
    _, r, d = _run(fx, "90-S-26PT-409_50663231")
    assert r.header.total_pkg == pytest.approx(12.0)
    assert "packing rows sum 1 != total_pkg 12" in (r.meta.notes or "")
    assert hard_check(d)["verdict"] == "pass"  # soft only


def test_pt4_soft_note_mixed_hs_lengths_50664217():
    fx = "pt4_50664217_layout.txt"
    if not (FIX / fx).is_file():
        pytest.skip("fixture missing")
    _, r, _ = _run(fx, "90-S-26PT-418_50664217")
    hs = {i.part_no: i.hs_code for i in r.items}
    assert hs["0.601.9E0.0C1"] == "84672920"  # kept as printed
    assert hs["0.601.9L6.0C0"] == "8467290000"
    assert "mixed HS digit lengths [8, 10]" in (r.meta.notes or "")


def test_pt4_pkg_fallback_vocab_without_shipping_unit():
    """Strip Shipping unit rows: new vocab + grand total still give the right pkg."""
    for fx, stem, want in (
        ("pt4_50665811_layout.txt", "50665811", 1.0),  # Slip sheet 1200* 800
        ("pt4_50654373_layout.txt", "50654373", 1.0),  # Bosch-Standard-Palette (HT) mit Box X03
        ("pt4_50654372_layout.txt.gz", "50654372", 30.0),  # Palette + Carton + Carton X02
    ):
        if not (FIX / fx).is_file():
            pytest.skip("fixture missing")
        text = re.sub(r"(?m)^.*Shipping unit.*$", "", _text(fx))
        r = pt_gloria_v1.extract_from_text(text, source_file=stem, text_backend="fixture")
        assert r.header.total_pkg == pytest.approx(want), stem


def test_pt4_type_summary_vocab_only():
    """No Shipping unit, no grand total: typed summary sum incl. new vocab."""
    snippet = """
Packing details
      Bosch-Standard-Palette (HT) mit Box X03                                        :    2
      Slip sheet     1200* 800                                                        :    1
      Carton X02                                                                      :    3
"""
    r = pt_gloria_v1.extract_from_text(snippet, source_file="vocab", text_backend="fixture")
    assert r.header.total_pkg == pytest.approx(6.0)
