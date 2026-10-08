"""Auditor re-review fixes (2026-10-05): clear BL faces must not stay needs_gold.

- BHC 4th case1 TVL HBL: page OCR 3488 / 3485 → clip re-reads 3185 (gold 3185)
- BHC 5th case1 TVL HBL: page OCR 1498.5 → clip re-reads 1195.5 (gold 1195.5)
- BHC 4th case6 JIFFA waybill: hatch removed → 16 / 1998 (was GW blank)
- BHC 4th case8 JIFFA waybill: 10 / 3084.5 now ≥2 agreeing reads (flag removed)

Unit tests feed fixture text + simulated re-reads; the ``real_*`` tests run
the original scans when they are present on this machine and tesseract is
installed (skipped otherwise, e.g. in CI).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_extractor.formats.bl import jif_cosmo_waybill_v1 as jif
from invoice_extractor.formats.bl import tvl_hbl_v1 as tvl

FX4 = Path(__file__).resolve().parents[1] / "fixtures" / "bhc4"
FX5 = Path(__file__).resolve().parents[1] / "fixtures" / "bhc5"
B4 = Path("/home/box/Downloads/BHC-batch-4th/BHC_4th data")
B5 = Path("/home/box/Downloads/BHC-batch-5th/BHC_5th data")


def _t(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _tvl(monkeypatch, text, t2, tok):
    monkeypatch.setattr(tvl, "_second_read", lambda path, backend: t2)
    monkeypatch.setattr(tvl, "_token_reads", lambda path, backend: tok)
    return tvl.extract("/x/scan.pdf", text, "ocr/tesseract", False).to_dict()


def test_tvl_4th_case1_token_rereads_outvote_page_misread(monkeypatch):
    t1 = _t(FX4 / "c1_tvl_hbl_ocr.txt")  # 200 dpi page: SHAKEL26871822 / 3488,000KGS
    t2 = t1.replace("SHAKEL26871822", "SHAKEL26971822").replace("3488,000KGS", "")  # 300 dpi: no GW
    tok = {
        "gw": [("tok200", 3185.0), ("tok300", 3185.0), ("tok400", 3185.0)],
        "bl_no": [("tok200", "SHAKEL26971822"), ("tok300", "SHAKEL26971822"), ("tok400", "SHAKEL26971822")],
        "note": "GW token '3488,000KGS' re-read",
    }
    d = _tvl(monkeypatch, t1, t2, tok)
    h, m = d["header"], d["meta"]
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == ("SHAKEL26971822", 8.0, 3185.0)
    assert not m["needs_gold"] and m["needs_gold_fields"] is None


def test_tvl_4th_case1_without_rereads_still_flags(monkeypatch):
    t1 = _t(FX4 / "c1_tvl_hbl_ocr.txt")
    t2 = t1.replace("SHAKEL26871822", "SHAKEL26971822").replace("3488,000KGS", "")
    d = _tvl(monkeypatch, t1, t2, {"gw": [], "bl_no": [], "note": None})
    assert set(d["meta"]["needs_gold_fields"]) >= {"bl_no", "gross_weight_kg"}


def test_tvl_5th_case1_token_rereads_fix_1498(monkeypatch):
    t1 = _t(FX5 / "c1_tvl_hbl_ocr.txt")  # face "18 PALLETS ! 1 1498.500KGS"
    tok = {"gw": [("tok200", 1195.5), ("tok300", 1195.5), ("tok400", 1195.5)],
           "bl_no": [("tok200", "SHAKEL26971867")] * 3, "note": None}
    d = _tvl(monkeypatch, t1, t1, tok)
    h, m = d["header"], d["meta"]
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == ("SHAKEL26971867", 6.0, 1195.5)
    assert m["needs_gold_fields"] is None


def test_tvl_token_rereads_that_disagree_do_not_override(monkeypatch):
    t1 = _t(FX5 / "c1_tvl_hbl_ocr.txt")
    t2 = t1.replace("1498.500KGS", "")
    tok = {"gw": [("tok200", 1195.5), ("tok300", 1495.5), ("tok400", 1196.5)], "bl_no": [], "note": None}
    d = _tvl(monkeypatch, t1, t2, tok)
    assert "gross_weight_kg" in (d["meta"]["needs_gold_fields"] or [])


def test_tvl_bl_no_with_space_parsed():
    v = tvl._read_votes("B/L NO. SHAKEL 26971822\n")
    assert v["bl_no"] == "SHAKEL26971822"


def _jif(monkeypatch, fixture, clean_fixture, tok):
    texts = [("clean", _t(FX4 / clean_fixture))] if clean_fixture else []
    no_loc = {"bl": [], "gw": [], "inv": [], "notes": []}  # located re-reads (round 2) off
    monkeypatch.setattr(jif, "_clean_passes",
                        lambda path, backend, page=0, want_inv=False: (texts, tok, [], no_loc))
    return jif.extract("/x/BL.pdf", _t(FX4 / fixture), "ocr/tesseract", False).to_dict()


def test_jif_case6_hatch_removed_pass_fills_gw(monkeypatch):
    tok = [("tok300", 1998.0), ("tok400", 1998.0), ("tok600", 1998.0)]
    d = _jif(monkeypatch, "c6_jif_waybill_ocr.txt", "c6_jif_waybill_clean_ocr.txt", tok)
    h, m = d["header"], d["meta"]
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == ("260918KEE103", 16.0, 1998.0)
    assert m["needs_gold_fields"] is None


def test_jif_case6_clean_page_alone_corroborates_pkg(monkeypatch):
    d = _jif(monkeypatch, "c6_jif_waybill_ocr.txt", "c6_jif_waybill_clean_ocr.txt", [])
    h, m = d["header"], d["meta"]
    assert h["packages"] == 16.0 and h["gross_weight_kg"] == 1998.0
    # one GW read only (clean page) → still needs_gold without the clip re-reads
    assert m["needs_gold_fields"] == ["gross_weight_kg"]


def test_jif_case8_flag_removed(monkeypatch):
    tok = [("tok300", 3084.5), ("tok400", 3084.5), ("tok600", 3084.5)]
    d = _jif(monkeypatch, "c8_jif_waybill_ocr.txt", "c8_jif_waybill_clean_ocr.txt", tok)
    h, m = d["header"], d["meta"]
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == ("260918KEE102", 10.0, 3084.5)
    assert m["needs_gold_fields"] is None
    assert h["vessel"] is None and h["measurement_cbm"] is None  # Result fields only


def test_remove_hlines_keeps_strokes_drops_hatch():
    pymupdf = pytest.importorskip("pymupdf")
    from invoice_extractor.ocr_reread import remove_hlines

    w, h = 20, 12
    px = bytearray(b"\xff" * (w * h))
    for x in range(w):
        px[3 * w + x] = 0  # 1-px hatch line
    for y in range(6, 11):
        for x in range(5, 8):
            px[y * w + x] = 0  # 5-px tall glyph stroke
    out = remove_hlines(pymupdf.Pixmap(pymupdf.csGRAY, w, h, bytes(px), 0), 3).samples
    assert all(out[3 * w + x] == 255 for x in range(w))
    assert all(out[y * w + x] == 0 for y in range(6, 11) for x in range(5, 8))


# ---------------------------------------------------------------- real scans

def _real(path: Path):
    from invoice_extractor.ocr import find_tesseract

    if not path.is_file() or find_tesseract() is None:
        pytest.skip("source scan / tesseract not available")
    from invoice_extractor.bl_rules_engine import extract_bl

    return extract_bl(path).to_dict()


@pytest.mark.parametrize(
    "path,fmt,bl_no,pkg,gw",
    [
        (B4 / "case 1" / "20260921141756-0001.pdf", "tvl_hbl_v1", "SHAKEL26971822", 8.0, 3185.0),
        (B4 / "case 6" / "BL.pdf", "jif_cosmo_waybill_v1", "260918KEE103", 16.0, 1998.0),
        (B4 / "case 8" / "WAYBILL.pdf", "jif_cosmo_waybill_v1", "260918KEE102", 10.0, 3084.5),
        (B5 / "case 1" / "20260929142515-0001.pdf", "tvl_hbl_v1", "SHAKEL26971867", 6.0, 1195.5),
    ],
)
def test_real_scan_gold(path, fmt, bl_no, pkg, gw):
    d = _real(path)
    h, m = d["header"], d["meta"]
    assert m["format_id"] == fmt
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == (bl_no, pkg, gw)
    assert not m["needs_gold"]
