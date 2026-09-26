"""SOE 2nd batch (invoice-only scope): soe_rb_gmbh_v1 extensions + thin-layer OCR retry."""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.formats import soe_rb_gmbh_v1
from invoice_extractor.formats.soe_rb_gmbh_v1 import normalize_ocr_partnumbers
from invoice_extractor.rules_engine import classify
from invoice_extractor.text_layer import text_layer_looks_thin

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def _text(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def _run(name: str, backend: str, fn: str = "x.pdf"):
    r = soe_rb_gmbh_v1.extract(fn, _text(name), backend, False)
    d = r.to_dict()
    return r, d, hard_check(d)


# fixture, backend, inv, date, amount, lines, qty, pkg, gw, origin, part_no[0], verdict
CASES = [
    ("soe2_7077520279_layout.txt", "pdftotext -layout", "7077520279", "2026-08-21",
     37174.27, 1, 3840.0, 2.0, 213.0, "CN", "0265.019.150-2CG", "pass"),
    ("soe2_7077515945_ocr.txt", "ocr/tesseract+thin_text_layer", "7077515945", "2026-08-19",
     2834.18, 3, 892.0, None, 24.0, None, "0263.036.668-2U1", "pass"),
    ("soe2_1267502206_ocr.txt", "ocr/tesseract", "7091801668", "2026-08-21",
     3642.15, 1, 112.0, 1.0, 16.0, "ES", "0265.011.097-57G", "pass"),
    # Auditor Round 2: print shows -57G on all three scans → pass.
    ("soe2_1267475174_ocr.txt", "ocr/tesseract", "7091801544", "2026-08-20",
     72843.01, 1, 2240.0, 5.0, 160.0, "ES", "0265.011.097-57G", "pass"),
    ("soe2_7405713_ocr.txt", "ocr/tesseract", "7091801079", "2026-08-13",
     3642.15, 1, 112.0, 1.0, 16.0, "ES", "0265.011.097-57G", "pass"),
    ("soe2_7369301_ocr.txt", "ocr/tesseract", "7091800640", "2026-08-06",
     21852.9, 1, 672.0, 2.0, 53.0, "ES", "0265.011.097-57G", "pass"),
]


@pytest.mark.parametrize(
    "fx,backend,inv,date,amt,lines,qty,pkg,gw,origin,pn0,verdict", CASES,
    ids=[c[0] for c in CASES],
)
def test_soe2_header_lines_and_hard_check(fx, backend, inv, date, amt, lines, qty, pkg,
                                          gw, origin, pn0, verdict):
    r, d, hc = _run(fx, backend)
    h = r.header
    assert r.meta.format_id == "soe_rb_gmbh_v1"
    assert h.invoice_no == inv
    assert h.invoice_date == date
    assert h.currency == "EUR"
    assert h.amount == pytest.approx(amt)
    assert r.meta.labeled_amount == pytest.approx(amt)
    assert r.meta.labeled_amount_label == "Invoice amount"
    assert len(r.items) == lines
    assert h.total_quantity == pytest.approx(qty)
    assert h.total_pkg == pkg
    assert h.gross_weight_kg == pytest.approx(gw)
    assert h.origin == origin
    assert r.items[0].part_no == pn0
    assert all(it.hs_code for it in r.items)  # SOE: HS required per line
    assert hc["verdict"] == verdict, hc
    if verdict == "needs_gold":
        # field-level needs_gold: every other hard check still ran clean
        assert r.meta.needs_gold_fields == ["items.part_no"]
        assert hc["issues"] == [
            "needs_gold field(s): items.part_no (document contradicts itself; "
            "confirm manually / from BL)"
        ]


def test_soe2_marking_gw_and_bare_origin_fallback_7077520279():
    r, _, _ = _run("soe2_7077520279_layout.txt", "pdftotext -layout")
    assert "Total gross weight" not in _text("soe2_7077520279_layout.txt")
    assert r.header.gross_weight_kg == pytest.approx(213.0)  # Marking "2 Pallets … Gross weight"
    assert r.items[0].origin == "CN"  # bare "CN" line, no per-line Net weight
    assert r.items[0].hs_code == "90318080"


def test_soe2_total_gross_weight_still_preferred_over_marking():
    t = _text("soe2_7077520279_layout.txt").replace(
        "Incoterms 2020:FCA Suzhou",
        "Incoterms 2020:FCA Suzhou\nTotal net weight : 161.280 KG   Total gross weight : 999.000 KG",
    )
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "pdftotext -layout", False)
    assert r.header.gross_weight_kg == pytest.approx(999.0)


def test_soe2_ocr_multi_page_three_lines_mixed_origin_7077515945():
    r, _, hc = _run("soe2_7077515945_ocr.txt", "ocr/tesseract+thin_text_layer")
    assert [it.part_no for it in r.items] == [
        "0263.036.668-2U1", "0263.036.669-2U1", "0215.000.838-2U1"]
    assert [it.origin for it in r.items] == ["DE", "DE", "CN"]
    assert [it.qty for it in r.items] == [292, 300, 300]
    assert [it.amount for it in r.items] == pytest.approx([959.42, 985.71, 889.05])
    assert {it.hs_code for it in r.items} == {"8708999900"}
    # Whitespace-only PN noise ("0263 .036.668-2U1") is a benign repair.
    assert not r.meta.needs_gold_fields
    # Page 3/3 (Marking) missing from the PDF → soft note, pkg stays empty.
    assert "SOFT: invoice page(s) 3/3 not in PDF" in (r.meta.notes or "")
    assert hc["verdict"] == "pass"


def test_soe2_thin_layer_detected_and_unclassified():
    thin = _text("soe2_7077515945_thinlayer.txt")
    assert text_layer_looks_thin(thin)
    fid, _score = classify(thin, "7077515945.pdf")
    assert fid is None
    assert not text_layer_looks_thin(_text("soe2_7077520279_layout.txt"))
    assert not text_layer_looks_thin("")


def test_soe2_thin_layer_retries_ocr_in_extract_invoice(monkeypatch, tmp_path):
    import invoice_extractor.ocr as ocr_mod
    import invoice_extractor.text_layer as tl
    from invoice_extractor.rules_engine import extract_invoice

    pdf = tmp_path / "7077515945.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(tl, "extract_text", lambda p, allow_ocr=True: (
        _text("soe2_7077515945_thinlayer.txt"), "pdftotext -layout", False))
    calls = []

    def fake_ocr(p, **kw):
        calls.append(p)
        return _text("soe2_7077515945_ocr.txt"), "ocr/tesseract", None

    monkeypatch.setattr(ocr_mod, "try_ocr_pdf", fake_ocr)
    r = extract_invoice(pdf)
    assert calls, "thin layer + no match must retry with OCR"
    assert r.meta.format_id == "soe_rb_gmbh_v1"
    assert r.meta.text_backend == "ocr/tesseract+thin_text_layer"
    assert r.header.invoice_no == "7077515945"
    assert hard_check(r.to_dict())["verdict"] == "pass"


def test_soe2_matching_layer_never_triggers_ocr_retry(monkeypatch, tmp_path):
    import invoice_extractor.ocr as ocr_mod
    import invoice_extractor.text_layer as tl
    from invoice_extractor.rules_engine import extract_invoice

    pdf = tmp_path / "7077520279.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(tl, "extract_text", lambda p, allow_ocr=True: (
        _text("soe2_7077520279_layout.txt"), "pdftotext -layout", False))

    def boom(*a, **k):
        raise AssertionError("OCR must not run for a layer that classifies")

    monkeypatch.setattr(ocr_mod, "try_ocr_pdf", boom)
    r = extract_invoice(pdf)
    assert r.meta.format_id == "soe_rb_gmbh_v1"
    assert r.meta.text_backend == "pdftotext -layout"


def test_soe2_normalize_ocr_partnumbers():
    t, mis = normalize_ocr_partnumbers("01 0263 .036.668-2U1 02630366682U1 292 328.57 959.42\n")
    assert t.startswith("01 0263.036.668-2U1 ")
    assert mis == []
    t, mis = normalize_ocr_partnumbers("01 0265.011, 097-576 0265011097576 672 3,251.92 21,852.90\n")
    assert t.startswith("01 0265.011.097-576 ")
    assert mis == ["0265.011, 097-576"]


def test_soe2_pn_rule_is_ocr_only():
    # Text layers are exact: a different variant elsewhere never rewrites
    # or flags the item row.
    t = _text("soe2_7077520279_layout.txt") + "\nRemark: replaces 0265.019.150-2CF\n"
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "pdftotext -layout", False)
    assert r.items[0].part_no == "0265.019.150-2CG"
    assert not r.meta.needs_gold_fields and not r.meta.notes
    assert hard_check(r.to_dict())["verdict"] == "pass"
    # Under OCR: 2CG×2 (Bosch + Customer PN) vs 2CF×1 → majority, keep 2CG.
    r2 = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r2.items[0].part_no == "0265.019.150-2CG"
    assert not r2.meta.needs_gold_fields


def test_soe2_ocr_pn_reconciled_7405713_minority_letter_reading():
    # Item row + Customer PN + one transport-order row all OCR as -576; the
    # transport order "026501109757GEC" reads -57G. 57G/576 are look-alikes →
    # letter form wins (print shows -57G; Auditor Round 2).
    r, _, hc = _run("soe2_7405713_ocr.txt", "ocr/tesseract")
    assert r.items[0].part_no == "0265.011.097-57G"
    assert not r.meta.needs_gold_fields and r.meta.needs_gold is False
    assert "readings -57G×1, -576×3 — " in r.meta.notes
    assert ", item row read -576" in r.meta.notes
    assert hc["verdict"] == "pass"


def test_soe2_ocr_pn_reconciled_7369301_separator_misread_corroborated():
    r, _, hc = _run("soe2_7369301_ocr.txt", "ocr/tesseract")
    assert r.items[0].part_no == "0265.011.097-57G"
    assert "readings -57G×2, -576×2" in r.meta.notes
    assert hc["verdict"] == "pass"


def test_soe2_ocr_pn_outlier_ignored_1267475174():
    r, _, _ = _run("soe2_1267475174_ocr.txt", "ocr/tesseract")
    assert r.items[0].part_no == "0265.011.097-57G"
    assert "outlier -876 ignored" in r.meta.notes
    assert not r.meta.needs_gold_fields


def test_soe2_pn_candidates_skip_numeric_fields():
    from invoice_extractor.formats.soe_rb_gmbh_v1 import _pn_candidates

    t = _text("soe2_7369301_ocr.txt")
    assert "26) Volume in cdm 576" in t
    cands = _pn_candidates(t, "0265011097")
    assert sorted(c for c, _ in cands) == ["576", "576", "57G", "57G"]
    # A PN-like number behind a numeric label is not part-number evidence.
    assert _pn_candidates("26) Volume in cdm 0265011097576\n", "0265011097") == []


def test_soe2_ocr_pn_unreconcilable_needs_gold():
    # 57G×2 (item row + Customer PN) + 57G×1 (p2) vs 5R9×3: no strict majority.
    t = _text("soe2_1267502206_ocr.txt") + (
        "\n1267502206 1 Pallets 02650110975R9\n"
        "Delivery 0265.011.097-5R9\nLabel 0265.011.097-5R9\n"
    )
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0265.011.097-57G"  # kept as read
    assert r.meta.needs_gold_fields == ["items.part_no"]
    assert "cannot be reconciled" in r.meta.notes
    assert hard_check(r.to_dict())["verdict"] == "needs_gold"


def test_soe2_ocr_pn_all_digit_suffix_kept():
    # No letter reading anywhere → nothing to reconcile; -576 stays.
    t = _text("soe2_7405713_ocr.txt").replace("026501109757GEC", "0265011097576EC")
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0265.011.097-576"
    assert not r.meta.needs_gold_fields


def test_soe2_ocr_separator_misread_without_corroboration_needs_gold():
    t = ("Invoice No. : 7091800640\nDate Invoice : 06.08.2026\n"
         "01 0265.011, 097-576 X1 672 3,251.92 21,852.90\n"
         "Sensor PC 100 EUR\nES 23.016 KG\nCustoms tariff no : 90318080\n"
         "Invoice amount: EUR 21,852.90\n")
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0265.011.097-576"
    assert r.meta.needs_gold_fields == ["items.part_no"]
    assert "no other PN reading" in r.meta.notes


def test_soe2_normalize_misread_list():
    _t, mis = normalize_ocr_partnumbers("01 0265 .011,097-57G 026501109757G 1 2 3\n")
    assert mis == ["0265 .011,097-57G"]


def test_soe2_typed_pallet_summary_without_cargo_list():
    t = _text("soe2_1267475174_ocr.txt")
    t = t.replace("Number of package: 5", "").replace("PAL:", "")
    assert "cardboard pallet" in t
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.header.total_pkg == 5.0


def test_soe2_thin_retry_skips_long_documents(monkeypatch, tmp_path):
    import invoice_extractor.ocr as ocr_mod
    import invoice_extractor.text_layer as tl
    from invoice_extractor.rules_engine import extract_invoice

    pdf = tmp_path / "Label_90-S-26MA-001.pdf"
    pdf.write_bytes(b"%PDF-1.4\n")
    long_thin = "\f".join(["SHIP TO 123"] * 24)
    monkeypatch.setattr(tl, "extract_text", lambda p, allow_ocr=True: (
        long_thin, "pdftotext -layout", False))

    def boom(*a, **k):
        raise AssertionError("no OCR retry for long thin documents")

    monkeypatch.setattr(ocr_mod, "try_ocr_pdf", boom)
    r = extract_invoice(pdf)
    assert r.meta.format_id is None
    assert r.meta.needs_gold is True


# --- Round 2b (Auditor rule risk): letter priority only for G/6 -------------

def _mini_invoice(pn: str, cust: str, extra: str = "") -> str:
    return (
        "Invoice No. : 7091800640\nDate Invoice : 06.08.2026\n"
        f"01 {pn} {cust} 672 3,251.92 21,852.90\n"
        "Sensor PC 100 EUR\nES 23.016 KG\nCustoms tariff no : 90318080\n"
        "Invoice amount: EUR 21,852.90\n" + extra
    )


def test_soe2_gg6_letter_wins_even_as_minority():
    # 57G×1 vs 576×3 (7405713 pattern) → G.
    t = _mini_invoice("0265.011.097-576", "0265011097576",
                      "Transport 026501109757GEC\nDelivery 0265011097576\n")
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0265.011.097-57G"
    assert not r.meta.needs_gold_fields


def test_soe2_digit_suffix_not_flipped_2u1_vs_zu1():
    # Real -2U1 read 3× as 2U1, 1× as ZU1 → stays 2U1 (Z/2 has no letter priority).
    t = _mini_invoice("0263.036.668-2U1", "02630366682U1",
                      "Cargo 0263.036.668-2U1\nTransport 0263036668ZU1\n")
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0263.036.668-2U1"
    assert not r.meta.needs_gold_fields
    assert "pos 1 2/Z → 2 (majority 3/4)" in r.meta.notes


def test_soe2_digit_suffix_restored_when_item_row_flipped_to_letter():
    # Item row OCR'd -ZU1 but 3 other PN readings say 2U1 → 2U1.
    t = _mini_invoice("0263.036.668-ZU1", "02630366682U1",
                      "Cargo 0263.036.668-2U1\nTransport 02630366682U1\n")
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0263.036.668-2U1"
    assert "item row read -ZU1" in r.meta.notes


def test_soe2_digit_suffix_not_flipped_501_vs_s01():
    t = _mini_invoice("0265.011.097-501", "0265011097501", "Cargo 0265011097S01\n")
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0265.011.097-501"
    assert not r.meta.needs_gold_fields


def test_soe2_digit_suffix_2u1_last_char_not_flipped_to_I():
    t = _mini_invoice("0263.036.668-2U1", "02630366682U1", "Cargo 0263036668 2UI\n")
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0263.036.668-2U1"


def test_soe2_non_g6_tie_needs_gold():
    # 2U1×2 vs ZU1×2 → tie at a non-G/6 position → needs_gold, value kept as read.
    t = _mini_invoice("0263.036.668-2U1", "02630366682U1",
                      "Cargo 0263.036.668-ZU1\nTransport 0263036668ZU1\n")
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0263.036.668-2U1"
    assert r.meta.needs_gold_fields == ["items.part_no"]
    assert "ties (only G/6 has letter priority)" in r.meta.notes
    assert hard_check(r.to_dict())["verdict"] == "needs_gold"


def test_soe2_non_g6_letter_needs_strict_majority():
    # S01×2 vs 501×1 → letter S is a strict majority by itself → S01.
    t = _mini_invoice("0265.011.097-S01", "0265011097S01", "Cargo 0265011097501\n")
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r.items[0].part_no == "0265.011.097-S01"
    assert not r.meta.needs_gold_fields
