"""MA 3rd Round 2 (2026-09-29): KWE sea waybill = Result BL columns only; OCR backend logging.

Rule (user): never extract fields that are not in ``InvoiceExtract_Result`` —
for a BL that is BL No. / BL Packages / BL G.W. Fixtures = Tesseract OCR of all
20 RBJPsea waybills (``fixtures/ma3_kwe_sea_<nnn>_ocr.txt``).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_extractor import text_layer
from invoice_extractor.checker import hard_check
from invoice_extractor.checker_bl import hard_check_bl
from invoice_extractor.formats.bl import kwe_sea_waybill_v1 as kwe
from invoice_extractor.pairing import merge_bl_onto_inv
from invoice_extractor.schema import ExtractResult, Header, Item, Meta

FIX = Path(__file__).resolve().parents[1] / "fixtures"


def _t(n: str) -> str:
    return (FIX / f"ma3_kwe_sea_{n}_ocr.txt").read_text(encoding="utf-8")


# folder: (waybill, pkg, GW) — printed values (Auditor review 2026-09-29: 20/20)
EXPECTED = {
    "012": ("122040099094", 15.0, 2962.0), "041": ("122040099422", 5.0, 431.0),
    "069": ("122040102071", 3.0, 345.0), "081": ("122040103342", 2.0, 69.0),
    "111": ("122040105313", 8.0, 846.0), "142": ("122040108220", 3.0, 240.0),
    "177": ("122040110434", 8.0, 976.0), "224": ("122040113525", 6.0, 510.0),
    "277": ("122040116093", 20.0, 1437.0), "312": ("122040119501", 12.0, 1649.0),
    "327": ("122040121310", 9.0, 804.8), "381": ("122040122986", 2.0, 393.0),
    "421": ("122040125241", 4.0, 529.0), "463": ("122040128973", 18.0, 1651.9),
    "513": ("122040131283", 14.0, 1252.0), "569": ("122040134551", 8.0, 834.3),
    "609": ("122040137793", 9.0, 1104.3), "660": ("122040141142", 12.0, 1126.4),
    "689": ("122040143706", 4.0, 216.9), "721": ("122040146602", 8.0, 320.8),
}
RESULT_BL_FIELDS = {"bl_no", "packages", "gross_weight_kg"}


@pytest.mark.parametrize("n", sorted(EXPECTED))
def test_kwe_all_20_result_fields_only(n):
    r = kwe.extract("robert bosch.pdf", _t(n), "ocr/tesseract", False)
    h = r.header
    assert (h.bl_no, h.packages, h.gross_weight_kg) == EXPECTED[n]
    # rule 2026-09-29: never extract fields that are not InvoiceExtract_Result columns
    extra = {k: v for k, v in h.to_dict().items() if v is not None and k not in RESULT_BL_FIELDS}
    assert extra == {}
    assert r.meta.needs_gold is False and not r.meta.needs_gold_fields
    assert hard_check_bl(r.to_dict())["verdict"] == "pass"


def test_result_bl_columns_are_the_only_bl_columns():
    from invoice_extractor.export import SUMMARY_COLS

    bl_cols = [c for c in SUMMARY_COLS if c.startswith("BL ")]
    assert bl_cols == ["BL No.", "BL Packages", "BL G.W. (kgs)"]
    assert kwe.RESULT_FIELDS == ("bl_no", "packages", "gross_weight_kg")


# ---------------------------------------- field-level BL needs_gold → INV row

def _inv() -> ExtractResult:
    return ExtractResult(
        header=Header(invoice_no="2000263341", amount=10.0, total_pkg=1.0, gross_weight_kg=5.0,
                      item_line_count=1, total_quantity=1.0, currency="TWD"),
        items=[Item(invoice_no="2000263341", part_no="0 986 000 000", qty=1.0, amount=10.0,
                    hs_code="8409991004", origin="Japan")],
        meta=Meta(source_file="x.pdf", format_id="ma_no_period_v1", confidence="rules",
                  labeled_amount=10.0, labeled_amount_label="Goods Value"),
    )


def test_bl_field_level_needs_gold_reaches_inv_row_exactly():
    out = merge_bl_onto_inv(
        _inv(),
        bl_header={"bl_no": "122040102071", "packages": 3.0, "gross_weight_kg": 345.0},
        bl_path="robert bosch.pdf",
        bl_format_id="kwe_sea_waybill_v1",
        bl_meta={"needs_gold": True, "needs_gold_fields": ["packages"],
                 "notes": "needs_gold: packages (OCR reads disagree / too few); GW reads: …"},
    )
    assert out.meta.needs_gold_fields == ["bl_packages"]  # not bl_gross_weight_kg (notes mention GW)
    assert hard_check(out.to_dict())["verdict"] == "needs_gold"


# ------------------------------------------- OCR backend logged for mojibake

def test_mojibake_layer_ocr_backend_is_tagged_and_logged(monkeypatch, caplog):
    layer = (FIX / "ma3_kwe_sea_513_mojibake_layer.txt").read_text(encoding="utf-8")
    ocr = _t("513")
    monkeypatch.setattr(text_layer, "extract_layout_text", lambda p: (layer, "pdftotext -layout", False))
    monkeypatch.setattr(text_layer, "try_ocr_pdf", lambda p: (ocr, "ocr/tesseract", None))
    with caplog.at_level("INFO", logger="invoice_extractor.text_layer"):
        text, backend, needs_ocr = text_layer.extract_text("robert bosch.pdf")
    assert text == ocr and needs_ocr is False
    assert backend == "ocr/tesseract+prefer_over_stale_layer+mojibake_layer"
    assert "ocr/tesseract+prefer_over_stale_layer+mojibake_layer" in caplog.text
    assert "mojibake" in caplog.text
    w = text_layer.backend_warning(backend)
    assert "unreliable" in w and backend in w


def test_empty_layer_backend_unchanged(monkeypatch):
    monkeypatch.setattr(text_layer, "extract_layout_text", lambda p: ("", "pdftotext -layout", True))
    monkeypatch.setattr(text_layer, "try_ocr_pdf", lambda p: (_t("041"), "ocr/tesseract", None))
    _, backend, _ = text_layer.extract_text("robert bosch.pdf")
    assert backend == "ocr/tesseract"
