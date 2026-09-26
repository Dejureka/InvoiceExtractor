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
    ("soe2_1267475174_ocr.txt", "ocr/tesseract", "7091801544", "2026-08-20",
     72843.01, 1, 2240.0, 5.0, 160.0, "ES", "0265.011.097-57G", "needs_gold"),
    ("soe2_7405713_ocr.txt", "ocr/tesseract", "7091801079", "2026-08-13",
     3642.15, 1, 112.0, 1.0, 16.0, "ES", "0265.011.097-576", "needs_gold"),
    ("soe2_7369301_ocr.txt", "ocr/tesseract", "7091800640", "2026-08-06",
     21852.9, 1, 672.0, 2.0, 53.0, "ES", "0265.011.097-576", "needs_gold"),
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


def test_soe2_ocr_suffix_conflict_needs_gold_7405713():
    r, _, _ = _run("soe2_7405713_ocr.txt", "ocr/tesseract")
    assert r.meta.needs_gold is True
    assert r.meta.confidence == "needs_gold"
    assert "suffix readings -57G" in r.meta.notes and "-576" in r.meta.notes


def test_soe2_ocr_separator_misread_needs_gold_7369301():
    r, _, _ = _run("soe2_7369301_ocr.txt", "ocr/tesseract")
    assert "OCR misread part no. separators (0265.011, 097-576)" in r.meta.notes
    assert r.meta.needs_gold_fields == ["items.part_no"]


def test_soe2_suffix_rule_is_ocr_only():
    # A text layer is exact: a second PN reading with another suffix (e.g. a
    # different variant in a remark) must not trigger the OCR-only rule.
    t = _text("soe2_7077520279_layout.txt") + "\nRemark: replaces 0265.019.150-2CF\n"
    r = soe_rb_gmbh_v1.extract("x.pdf", t, "pdftotext -layout", False)
    assert not r.meta.needs_gold_fields
    assert hard_check(r.to_dict())["verdict"] == "pass"
    r2 = soe_rb_gmbh_v1.extract("x.pdf", t, "ocr/tesseract", False)
    assert r2.meta.needs_gold_fields == ["items.part_no"]


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
