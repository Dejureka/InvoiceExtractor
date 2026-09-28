"""MA 3rd batch (RBDEsea 90-C COSCO arrival + RBJPsea 90-KWE sea waybill scans)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_extractor.bl_rules_engine import classify_bl, looks_like_bl_filename
from invoice_extractor.checker import hard_check
from invoice_extractor.checker_bl import hard_check_bl
from invoice_extractor.formats.bl import cosco_arrival_v1, kwe_air_waybill_v1, kwe_sea_waybill_v1
from invoice_extractor.pairing import merge_bl_onto_inv
from invoice_extractor.schema import ExtractResult, Header, Item, Meta
from invoice_extractor.text_layer import (
    text_layer_looks_mojibake,
    text_layer_looks_unreliable,
)

FIX = Path(__file__).resolve().parents[1] / "fixtures"
MA3 = Path("/home/box/Downloads/MA-batch-final/MA_3rd data/3rd data")


def _t(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


# ---------------------------------------------------------------- COSCO (DE)

@pytest.mark.parametrize(
    "fx,fn,bl,pkg,gw,eta,vessel,voy,pod,cont,refs",
    [
        ("ma3_cosco_BL6437826540_layout.txt", "BL6437826540.PDF", "COSU6437826540", 33.0,
         2457.362, "2026-02-21", "EVER AEON", "1372-006E", "Taipei Port",
         "CSNU1608356/RC306452", "2120419937, 2120419938"),
        ("ma3_cosco_BL6447417770_layout.txt", "BL6447417770.PDF", "COSU6447417770", 22.0,
         18410.0, "2026-05-07", "EVER ACE", "1384-017E", "Kaohsiung",
         "TGBU8778220/PY314071", "2120462728, 2120462729"),
    ],
)
def test_cosco_arrival_extract(fx, fn, bl, pkg, gw, eta, vessel, voy, pod, cont, refs):
    text = _t(fx)
    fid, score = classify_bl(text, fn)
    assert fid == "cosco_arrival_v1" and score >= 0.9
    r = cosco_arrival_v1.extract(fn, text, "pdftotext -layout", False)
    h = r.header
    assert h.bl_no == bl
    assert h.packages == pkg
    assert h.gross_weight_kg == pytest.approx(gw)
    assert h.eta == eta
    assert (h.vessel, h.voyage, h.pod) == (vessel, voy, pod)
    assert h.container_nos == cont
    assert h.load_type == "FCL"
    assert h.invoice_refs == refs
    assert r.meta.needs_gold is False
    assert hard_check_bl(r.to_dict())["verdict"] == "pass"


def test_cosco_total_vs_container_row_mismatch_is_needs_gold():
    text = _t("ma3_cosco_BL6437826540_layout.txt").replace(
        "Total:                33   2457.362 KG", "Total:                34   2457.362 KG"
    )
    r = cosco_arrival_v1.extract("BL6437826540.PDF", text, "pdftotext -layout", False)
    assert r.meta.needs_gold is True
    assert "container rows" in (r.meta.notes or "")
    assert hard_check_bl(r.to_dict())["verdict"] == "needs_gold"


def test_bl_plus_ten_digit_filename_is_bl():
    assert looks_like_bl_filename("BL6437826540.PDF")
    assert not looks_like_bl_filename("INVOICE 2120419937.PDF")
    assert not looks_like_bl_filename("BLUE_2120419937.PDF")


# ---------------------------------------------------------- KWE sea (JP scans)

@pytest.mark.parametrize(
    "fx,bl,pkg,gw,etd",
    [
        ("ma3_kwe_sea_041_ocr.txt", "122040099422", 5.0, 431.0, "2026-01-13"),
        # page 2 = ATTACHED SHEET (no freight-invoice PCS/KG line)
        ("ma3_kwe_sea_277_ocr.txt", "122040116093", 20.0, 1437.0, "2026-04-13"),
        # OCR glued a stray '4' in front of WAYBILL NO. (4122040119501)
        ("ma3_kwe_sea_312_ocr.txt", "122040119501", 12.0, 1649.0, "2026-04-24"),
    ],
)
def test_kwe_sea_waybill_ocr_votes(fx, bl, pkg, gw, etd):
    text = _t(fx)
    fid, _ = classify_bl(text, "robert bosch.pdf")
    assert fid == "kwe_sea_waybill_v1"
    assert kwe_air_waybill_v1.match_score(text, "robert bosch.pdf") < kwe_sea_waybill_v1.match_score(
        text, "robert bosch.pdf"
    )
    r = kwe_sea_waybill_v1.extract("robert bosch.pdf", text, "ocr/tesseract", False)
    h = r.header
    assert (h.bl_no, h.packages, h.gross_weight_kg, h.etd) == (bl, pkg, gw, etd)
    assert h.pol == "YOKOHAMA" and h.pod == "KEELUNG"
    assert r.meta.needs_gold is False
    assert hard_check_bl(r.to_dict())["verdict"] == "pass"


def test_kwe_sea_disagreeing_reads_go_needs_gold():
    text = _t("ma3_kwe_sea_041_ocr.txt")
    # corrupt two of the three GW reads differently → no ≥2 agreement
    bad = text.replace("SAID TO CONTAIN: 431.00", "SAID TO CONTAIN: 481.00", 1).replace(
        "5 PCS 431.00 KG", "5 PCS 437.00 KG", 1
    )
    r = kwe_sea_waybill_v1.extract("robert bosch.pdf", bad, "ocr/tesseract", False)
    assert r.meta.needs_gold is True
    assert "gross_weight_kg" in r.meta.notes
    assert r.header.packages == 5.0  # packages reads still agree
    assert hard_check_bl(r.to_dict())["verdict"] == "needs_gold"


def test_kwe_sea_single_read_is_not_enough():
    text = _t("ma3_kwe_sea_041_ocr.txt")
    only_one = "\n".join(
        ln for ln in text.splitlines()
        if "431.00" not in ln or "SAID TO CONTAIN" in ln
    )
    r = kwe_sea_waybill_v1.extract("robert bosch.pdf", only_one, "ocr/tesseract", False)
    assert r.header.gross_weight_kg == 431.0  # suggested value kept
    assert r.meta.needs_gold is True


def test_kwe_sea_does_not_take_air_waybill():
    text = _t("soe_kwe_hawb_layout.txt")
    assert kwe_sea_waybill_v1.match_score(text, "122019555195-HAWC.pdf") < 0.3
    fid, _ = classify_bl(text, "122019555195-HAWC.pdf")
    assert fid == "kwe_air_waybill_v1"


# ------------------------------------------------------------- mojibake layer

def test_scanner_cjk_mojibake_layer_detected():
    layer = _t("ma3_kwe_sea_513_mojibake_layer.txt")
    assert text_layer_looks_mojibake(layer)
    assert text_layer_looks_unreliable(layer)


@pytest.mark.parametrize(
    "fx",
    ["ma3_cosco_BL6437826540_layout.txt", "soe_kwe_hawb_layout.txt", "soe2_7077520279_layout.txt"],
)
def test_clean_layers_are_not_mojibake(fx):
    assert not text_layer_looks_mojibake(_t(fx))


# -------------------------------------------- BL needs_gold reaches INV row

def _inv() -> ExtractResult:
    return ExtractResult(
        header=Header(invoice_no="2000262944", amount=10.0, total_pkg=1.0, gross_weight_kg=5.0,
                      item_line_count=1, total_quantity=1.0, currency="TWD"),
        items=[Item(invoice_no="2000262944", part_no="0 986 000 000", qty=1.0, amount=10.0,
                    hs_code="8409991004", origin="Japan")],
        meta=Meta(source_file="x.pdf", format_id="ma_no_period_v1", confidence="rules",
                  labeled_amount=10.0, labeled_amount_label="Goods Value"),
    )


def test_bl_needs_gold_flags_inv_row_fields():
    out = merge_bl_onto_inv(
        _inv(),
        bl_header={"bl_no": "122040099422", "packages": 5.0, "gross_weight_kg": 431.0},
        bl_path="robert bosch.pdf",
        bl_format_id="kwe_sea_waybill_v1",
        bl_meta={"needs_gold": True, "notes": "needs_gold: gross_weight_kg (OCR reads disagree / too few)"},
    )
    assert out.header.bl_gross_weight_kg == 431.0
    assert out.meta.needs_gold_fields == ["bl_gross_weight_kg"]
    assert "bl_needs_gold" in out.meta.notes
    assert hard_check(out.to_dict())["verdict"] == "needs_gold"


def test_bl_ok_keeps_inv_pass():
    out = merge_bl_onto_inv(
        _inv(),
        bl_header={"bl_no": "122040099422", "packages": 5.0, "gross_weight_kg": 431.0},
        bl_path="robert bosch.pdf",
        bl_format_id="kwe_sea_waybill_v1",
        bl_meta={"needs_gold": False},
    )
    assert not out.meta.needs_gold_fields
    assert hard_check(out.to_dict())["verdict"] == "pass"


# ------------------------------------------------ real-sample smoke (optional)

@pytest.mark.parametrize(
    "folder,n_inv,bl_fmt,bl_no,bl_pkg,bl_gw",
    [
        ("RBDEsea/90-C-26MA-190", 1, "cosco_arrival_v1", "COSU6445127890", 34.0, 2652.171),
        ("RBJPsea/90-KWE-26MA-081", 2, "kwe_sea_waybill_v1", "122040103342", 2.0, 69.0),
    ],
)
def test_ma3_folder_pairs_inv_with_bl(folder, n_inv, bl_fmt, bl_no, bl_pkg, bl_gw):
    d = MA3 / folder
    if not d.is_dir():
        pytest.skip(f"missing {d}")
    from invoice_extractor.ocr import tesseract_available
    if bl_fmt == "kwe_sea_waybill_v1" and not tesseract_available():
        pytest.skip("tesseract not available")
    from invoice_extractor.pairing import auto_pair, extract_pair_row

    rows = [r for r in auto_pair(sorted(d.iterdir())) if r.inv_path]
    assert len(rows) == n_inv
    for row in rows:
        data = extract_pair_row(row)
        m, h = data["meta"], data["header"]
        assert m["bl_format_id"] == bl_fmt
        assert (h["bl_no"], h["bl_packages"], h["bl_gross_weight_kg"]) == (bl_no, bl_pkg, bl_gw)
        assert data["_hard"]["verdict"] == "pass"
        assert all(it.get("hs_code") for it in data["items"])
