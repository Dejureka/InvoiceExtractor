"""BHC 4th batch (2026-10-05) FormatSOP regression.

Text fixtures in ``fixtures/bhc4/`` are the exact text the extractor sees
(pdftotext layout / openpyxl / xlrd cell text / Tesseract OCR). Covers:

- new layout family ``bhc_vendor_ci_v1`` (profiles sanhua / welling /
  broad_ocean / hipus / hailiang) + its split-PKL hook ``parse_packing``
- ``suzhou_aichi_v1`` generalised (STATOR+ROTOR rows, labeled TOTAL, Gross GW)
- ``hitachi_gls_v1`` inline-accessory layout (MEH6J044)
- ``tvl_hbl_v1`` vote over container rows / SAY TOTAL / face (+ QDEX photo B/L)
- new BL format ``jif_cosmo_waybill_v1`` (JIFFA / Cosmo Trans Line waybill)
- pairing: ``CI`` token, shared PKL, duplicate BL copies, empty Excel template,
  vendor-aware PKL overlay, twin rows in shipment_first dedupe
- image (.jpg) input routing
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.rules_engine import extract_invoice

FX = Path(__file__).resolve().parents[1] / "fixtures" / "bhc4"


def _t(name: str) -> str:
    return (FX / name).read_text(encoding="utf-8")


def _inv(fixture: str, filename: str, backend: str = "pdftotext -layout"):
    r = extract_invoice(Path("/nonexistent") / filename, text=_t(fixture), backend=backend, needs_ocr=False)
    d = r.to_dict()
    return d, hard_check(d)


# --------------------------------------------------------------------------- suzhou / hitachi

def test_suzhou_aichi_4th_stator_rotor_gross_weight():
    d, hard = _inv("c2_suzhou_aichi_ocr.txt", "SATJG26011.pdf", "ocr/tesseract")
    h = d["header"]
    assert d["meta"]["format_id"] == "suzhou_aichi_v1"
    assert h["invoice_no"] == "SATJG26011"
    assert h["amount"] == pytest.approx(66150.64)
    assert len(d["items"]) == 2
    assert (h["total_pkg"], h["gross_weight_kg"]) == (12.0, 7574.0)  # Gross, not Net 7277
    assert h["incoterm"] == "FOB SHANGHAI"  # read from page, no SHENZHEN default
    assert hard["verdict"] == "pass"


def test_suzhou_aichi_3rd_unchanged():
    d, hard = _inv("b3c1_suzhou_aichi_ocr.txt", "SATJG26010.pdf")
    h = d["header"]
    assert d["meta"]["format_id"] == "suzhou_aichi_v1"
    assert h["amount"] == pytest.approx(40875)
    assert (h["total_pkg"], h["gross_weight_kg"]) == (7.0, 4121.0)
    assert hard["verdict"] == "pass"


def test_hitachi_gls_inline_accessory_layout():
    d, hard = _inv("c6_hitachi_MEH6J044.txt", "20260923_MEH6J044(TX14,TX17,TX21,TY06,TY27,TY41).pdf")
    h = d["header"]
    assert d["meta"]["format_id"] == "hitachi_gls_v1"
    assert h["invoice_no"] == "MEH6J044"
    assert h["amount"] == pytest.approx(18143405)
    assert len(d["items"]) == 7
    assert (h["total_pkg"], h["gross_weight_kg"]) == (16.0, 1998.0)
    assert h["incoterm"] == "F.O.B. SHIMIZU, JAPAN"
    assert all(it["part_no"] for it in d["items"])
    assert hard["verdict"] == "pass"


def test_hitachi_gls_old_layout_unchanged():
    d, hard = _inv("mega_hitachi_MEH6A036.txt", "SD(TW)_20260126_MEH6A036(TW99,TX68 etc).pdf")
    assert d["meta"]["format_id"] == "hitachi_gls_v1"
    assert len(d["items"]) == 16
    assert (d["header"]["total_pkg"], d["header"]["gross_weight_kg"]) == (2.0, 359.0)
    assert hard["verdict"] == "pass"


# --------------------------------------------------------------------------- bhc_vendor_ci_v1

@pytest.mark.parametrize(
    "fixture,filename,inv_no,amount,lines,pkg,gw,incoterm,profile",
    [
        ("c1_sanhua_pdf.txt", "SHC-THT2609029客户资料.pdf", "SHC/THT2609029", 27623.74, 6, 8.0, 3185.0, "FOB SHANGHAI", "sanhua"),
        ("c1_sanhua_xls.txt", "SHC-THT2609029客户资料.xls", "SHC/THT2609029", 27623.74, 6, 8.0, 3185.0, "FOB SHANGHAI", "sanhua"),
        ("c10_welling_pdf.txt", "CI PL MDBWHTWJCH260915.pdf", "MDBWHTWJCH260915", 126756.0, 3, 63.0, 28972.8, "FOB BEIJIAO", "welling"),
        ("c11_broad_ocean_inv_xls.txt", "COMMERCIAL_INVOICE BHC-TW 2026-09-23.xls", "2026-09-23-BHC-TW", 13641.6, 1, None, None, "FOB ZhongShan", "broad_ocean"),
        ("c8_hipus_117_pdf.txt", "IV_117-BHCTW-26K-41.PDF", "117-BHCTW-26K-41", 10014860.0, 43, None, None, "FOB", "hipus"),
        ("c8_hipus_117_xlsx.txt", "IV_117-BHCTW-26K-41.xlsx", "117-BHCTW-26K-41", 10014860.0, 43, None, None, "FOB", "hipus"),
        ("c8_hipus_121_pdf.txt", "IV_121-BHCTW-26K-37.PDF", "121-BHCTW-26K-37", 15300.0, 1, None, None, "FOB", "hipus"),
        ("c8_hipus_121_xlsx.txt", "IV_121-BHCTW-26K-37.xlsx", "121-BHCTW-26K-37", 15300.0, 1, None, None, "FOB", "hipus"),
        ("c5_hailiang_xlsx.txt", "26HLHK01Q10009B-发票箱单.xlsx", "26HLHK01Q10009B", 770025.9, 1, 54.0, 54288.0, "FOB SHANGHAI", "hailiang"),
    ],
)
def test_bhc_vendor_ci_profiles(fixture, filename, inv_no, amount, lines, pkg, gw, incoterm, profile):
    backend = "excel/openpyxl" if filename.endswith(("xlsx", "xls")) else "pdftotext -layout"
    d, hard = _inv(fixture, filename, backend)
    h = d["header"]
    assert d["meta"]["format_id"] == "bhc_vendor_ci_v1"
    assert f"profile={profile}" in (d["meta"]["notes"] or "")
    assert h["invoice_no"] == inv_no
    assert h["amount"] == pytest.approx(amount)
    assert len(d["items"]) == lines
    assert h["total_pkg"] == pkg and h["gross_weight_kg"] == gw
    assert h["incoterm"] == incoterm
    assert hard["verdict"] == "pass"


def test_hipus_pdf_and_xlsx_twin_lines_identical():
    a, _ = _inv("c8_hipus_117_pdf.txt", "IV_117-BHCTW-26K-41.PDF")
    b, _ = _inv("c8_hipus_117_xlsx.txt", "IV_117-BHCTW-26K-41.xlsx", "excel/openpyxl")
    key = lambda it: (it["part_no"], it["qty"], it["amount"], it["origin"])  # noqa: E731
    assert [key(i) for i in a["items"]] == [key(i) for i in b["items"]]


def test_sanhua_pdf_blank_customer_no_is_noted():
    d, _ = _inv("c1_sanhua_pdf.txt", "SHC-THT2609029客户资料.pdf")
    blank = [it for it in d["items"] if not it["part_no"]]
    assert len(blank) == 1
    assert "P10062198" in (d["meta"]["notes"] or "")


def test_vendor_ci_parse_packing_hooks():
    from invoice_extractor.formats import bhc_vendor_ci_v1 as m

    bo = m.parse_packing(_t("c11_broad_ocean_pkl_xls.txt"))
    assert (bo["pkg"], bo["gw"]) == (7.0, 1876.0)
    hp = m.parse_packing(_t("c8_hipus_pl_xlsx.txt"))
    assert (hp["pkg"], hp["gw"]) == (10.0, 3084.5)
    assert len(hp["units"]) == 10 and sum(hp["units"].values()) == pytest.approx(3084.5)


def test_vendor_ci_does_not_claim_bl_text():
    from invoice_extractor.formats import bhc_vendor_ci_v1 as m

    assert m.match_score(_t("c1_tvl_hbl_ocr.txt"), "20260921141756-0001.pdf") < 0.3


# --------------------------------------------------------------------------- BL formats

def _bl(fixture: str, filename: str):
    from invoice_extractor.bl_rules_engine import extract_bl

    # nonexistent path → no second OCR pass (text-only vote)
    return extract_bl(Path("/nonexistent") / filename, text=_t(fixture), backend="ocr/tesseract", needs_ocr=False).to_dict()


@pytest.mark.parametrize(
    "fixture,filename,bl_no,pkg,gw",
    [
        ("c2_tvl_hbl_ocr.txt", "20260923094309-0001.pdf", "SHAKEL26971920", 12.0, 7574.0),  # SAY TOTAL TWELVE (12)
        ("c5_tvl_hbl_ocr.txt", "20260922194949-0001.pdf", "SHAKEL26971161", 54.0, 54288.0),  # 10+22+22 rows
        ("c7_tvl_hbl_ocr.txt", "SHAKEL26971969.pdf", "SHAKEL26971969", 90.0, 21870.0),  # 3×30 CARTONS
        ("c3_tvl_qdex_jpg_ocr.txt", "QDEX2609096.jpg", "QDEX2609096", 30.0, 4500.0),  # photo B/L
    ],
)
def test_tvl_votes(fixture, filename, bl_no, pkg, gw):
    d = _bl(fixture, filename)
    assert d["meta"]["format_id"] == "tvl_hbl_v1"
    h = d["header"]
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == (bl_no, pkg, gw)


def test_tvl_container_count_never_used_as_packages():
    d = _bl("c5_tvl_hbl_ocr.txt", "x.pdf")
    assert d["header"]["packages"] != 1.0  # "ONE 20'GP AND TWO 40'HC CONTAINERS"


def test_tvl_bl_no_disagreement_flags_needs_gold():
    from invoice_extractor.formats.bl import tvl_hbl_v1 as m

    t1 = _t("c1_tvl_hbl_ocr.txt")  # 200 dpi read: SHAKEL26871822 / 3488
    # 300 dpi read (as observed): BL no right, face GW not readable at all
    t2 = t1.replace("SHAKEL26871822", "SHAKEL26971822").replace("3488,000KGS", "")
    orig = m._second_read
    try:
        m._second_read = lambda path, backend: t2  # type: ignore[assignment]
        d = m.extract("/x/20260921141756-0001.pdf", t1, "ocr/tesseract", False).to_dict()
    finally:
        m._second_read = orig  # type: ignore[assignment]
    assert set(d["meta"]["needs_gold_fields"]) >= {"bl_no", "gross_weight_kg"}
    assert d["header"]["packages"] == 8.0


def test_tvl_words_to_int():
    from invoice_extractor.formats.bl.tvl_hbl_v1 import _words_to_int

    assert _words_to_int("ONE HUNDRED AND SIXTY-NINE") == 169
    assert _words_to_int("TWELVE") == 12
    assert _words_to_int("2NEME") is None


@pytest.mark.parametrize(
    "fixture,bl_no,pkg,gw,ng",
    [
        ("c6_jif_waybill_ocr.txt", "260918KEE103", 16.0, None, {"packages", "gross_weight_kg"}),
        ("c8_jif_waybill_ocr.txt", "260918KEE102", 10.0, 3084.5, {"packages", "gross_weight_kg"}),
    ],
)
def test_jif_cosmo_waybill(fixture, bl_no, pkg, gw, ng):
    d = _bl(fixture, "BL.pdf")
    assert d["meta"]["format_id"] == "jif_cosmo_waybill_v1"
    h = d["header"]
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == (bl_no, pkg, gw)
    assert set(d["meta"]["needs_gold_fields"]) == ng  # single OCR read → needs_gold (KWE policy)
    # Result fields only
    assert h["vessel"] is None and h["voyage"] is None and h["measurement_cbm"] is None


def test_waybill_filename_is_bl():
    from invoice_extractor.bl_rules_engine import looks_like_bl_filename

    assert looks_like_bl_filename("WAYBILL.pdf")
    assert not looks_like_bl_filename("IV_117-BHCTW-26K-41.PDF")


# --------------------------------------------------------------------------- pairing

def test_ci_token_is_invoice():
    from invoice_extractor.pairing import classify_role

    r = classify_role(Path("/c/CI PL MDBWHTWJCH260915.pdf"), filename_only=True)
    assert r.role == "combined"


def _roles(names, d="/c8"):
    from invoice_extractor.pairing import classify_role

    return [classify_role(Path(d) / n, filename_only=True) for n in names]


def test_shared_pkl_attached_to_all_invoices():
    from invoice_extractor.pairing import STATUS_INV_PKL, auto_pair

    names = ["IV_117-BHCTW-26K-41.PDF", "IV_117-BHCTW-26K-41.xlsx", "IV_121-BHCTW-26K-37.PDF",
             "IV_121-BHCTW-26K-37.xlsx", "PL_117-BHCTW-26K-41, 121-BHCTW-26K-37.xlsx"]
    rows = auto_pair([Path("/c8") / n for n in names], roles=_roles(names))
    inv_rows = [r for r in rows if r.inv_path]
    assert len(inv_rows) == 4
    assert all(r.status == STATUS_INV_PKL and r.pkl_path.name.startswith("PL_") for r in inv_rows)
    assert all("shared PKL" in r.notes for r in inv_rows)
    assert not [r for r in rows if r.pkl_path and not r.inv_path]


def test_duplicate_bl_copies_collapse(monkeypatch):
    from invoice_extractor import pairing

    fake = {
        "WAYBILL.pdf": {"header": {"bl_no": "260918KEE102", "packages": 10.0, "gross_weight_kg": 3084.5},
                        "meta": {"needs_gold": True, "needs_gold_fields": ["packages"]}},
        "20260921195744-0001.pdf": {"header": {"bl_no": "260918KEE102", "packages": None, "gross_weight_kg": None},
                                    "meta": {"needs_gold": True, "needs_gold_fields": ["packages", "gross_weight_kg"]}},
    }
    monkeypatch.setattr(pairing, "_extract_bl_cached", lambda p: copy.deepcopy(fake[Path(p).name]))
    names = ["IV_117-BHCTW-26K-41.PDF", "IV_121-BHCTW-26K-37.PDF", "WAYBILL.pdf", "20260921195744-0001.pdf"]
    roles = _roles(names)
    for r in roles:
        if r.path.name.startswith("2026"):
            r.role = "bl"
    rows = pairing.auto_pair([r.path for r in roles], roles=roles)
    inv_rows = [r for r in rows if r.inv_path]
    assert {r.bl_path.name for r in inv_rows} == {"WAYBILL.pdf"}
    assert all("duplicate BL copy 20260921195744-0001.pdf" in r.notes for r in inv_rows)
    assert not [r for r in rows if r.bl_path and not r.inv_path]


def test_empty_excel_template_skipped(tmp_path):
    from openpyxl import Workbook

    from invoice_extractor.pairing import auto_pair, excel_looks_empty

    empty = tmp_path / "SSLJP0023526  MEH6J044.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["SHGDL0219"])
    ws.append(["Invoice No.", "Date"])
    ws.append(["Marks & Numbers", "Description", "Quantity", "Unit Price", "Total Amount"])
    wb.save(empty)
    full = tmp_path / "INV 9027.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["Invoice No.", "9027000001"])
    ws.append(["PN", "Qty", "Price", "Amount"])
    ws.append(["3EF59091A", 10, 2.5, 25.0])
    wb.save(full)
    assert excel_looks_empty(empty)
    assert not excel_looks_empty(full)
    rows = auto_pair([empty, full])
    sk = [r for r in rows if r.skipped]
    assert len(sk) == 1 and sk[0].inv_path == empty and "empty Excel template" in sk[0].notes


def test_pkl_overlay_uses_format_parser():
    from invoice_extractor.pairing import merge_pkl_onto_inv, parse_packing_pkg_gw
    from invoice_extractor.schema import ExtractResult, Header, Meta

    pkl = _t("c11_broad_ocean_pkl_xls.txt")
    assert parse_packing_pkg_gw(pkl)[0] != 7.0  # generic parser mis-reads (2352 pcs)
    inv = ExtractResult(header=Header(invoice_no="2026-09-23-BHC-TW"), items=[],
                        meta=Meta(source_file="/c11/inv.xls", format_id="bhc_vendor_ci_v1"))
    out = merge_pkl_onto_inv(inv, pkl_text=pkl, pkl_path="/c11/pkl.xls")
    assert (out.header.total_pkg, out.header.gross_weight_kg) == (7.0, 1876.0)
    assert "pkl_parser=bhc_vendor_ci_v1" in out.meta.notes

    pl = _t("c8_hipus_pl_xlsx.txt")
    inv2 = ExtractResult(header=Header(invoice_no="117-BHCTW-26K-41"), items=[],
                         meta=Meta(source_file="/c8/IV_117.PDF", format_id="bhc_vendor_ci_v1"))
    out2 = merge_pkl_onto_inv(inv2, pkl_text=pl, pkl_path="/c8/PL.xlsx")
    assert len(out2.meta.packing_units) == 10


def test_shipment_first_twin_rows_share_first_invoice_total():
    from invoice_extractor.pairing import dedupe_shared_packing_units

    units = {f"PALLET-{i}": 308.45 for i in range(1, 11)}

    def d(inv, src):
        return {"header": {"invoice_no": inv, "total_pkg": 10.0, "gross_weight_kg": 3084.5, "bl_no": "260918KEE102",
                           "amount": 1.0, "item_line_count": 1, "total_quantity": 1.0},
                "items": [{"part_no": "3EJ45739A", "qty": 1.0, "amount": 1.0}],
                "meta": {"source_file": f"/c8/{src}", "inv_file": f"/c8/{src}", "packing_units": dict(units),
                         "format_id": "bhc_vendor_ci_v1"}}

    ds = [d("117-BHCTW-26K-41", "IV_117.PDF"), d("117-BHCTW-26K-41", "IV_117.xlsx"),
          d("121-BHCTW-26K-37", "IV_121.PDF"), d("121-BHCTW-26K-37", "IV_121.xlsx")]
    dedupe_shared_packing_units(ds)
    got = {(x["header"]["invoice_no"], Path(x["meta"]["source_file"]).suffix): (x["header"]["total_pkg"], x["header"]["gross_weight_kg"]) for x in ds}
    assert got[("117-BHCTW-26K-41", ".PDF")] == (10.0, 3084.5)
    assert got[("117-BHCTW-26K-41", ".xlsx")] == (10.0, 3084.5)
    assert got[("121-BHCTW-26K-37", ".PDF")] == (0.0, 0.0)
    assert got[("121-BHCTW-26K-37", ".xlsx")] == (0.0, 0.0)
    assert "one shared PL" in ds[0]["header"]["summary_note"]


# --------------------------------------------------------------------------- image input

def test_image_input_routing(tmp_path, monkeypatch):
    from invoice_extractor import text_layer
    from invoice_extractor.cli import collect_pdfs

    jpg = tmp_path / "QDEX2609096.jpg"
    jpg.write_bytes(b"\xff\xd8\xff\xe0fake")
    png = tmp_path / "Summary_example.png"
    png.write_bytes(b"\x89PNGfake")
    files, _ = collect_pdfs([tmp_path])
    assert jpg in files and png not in files  # PNG only as an explicit file
    files2, _ = collect_pdfs([png])
    assert png in files2

    t, b, need = text_layer.extract_layout_text(jpg)
    assert (t, b, need) == ("", "image", True)
    monkeypatch.setattr(text_layer, "try_ocr_image", lambda p: ("B/L NO. QDEX2609096", "ocr/tesseract+image", None))
    t, b, need = text_layer.extract_text(jpg)
    assert b == "ocr/tesseract+image" and not need and "QDEX" in t
