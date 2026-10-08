"""BHC 6th batch (2026-10-08) FormatSOP regression.

Text fixtures in ``fixtures/bhc6/`` cover:

- ``bhc_vendor_ci_v1`` new profiles ``topband`` (PDF INV + .xls PL),
  ``augewei`` / ``jiangnan`` (PDF INV + PL), ``wolong`` (xlsx / xls combined;
  amount-in-words mismatch → numeric total + note), ``saginomiya`` (PDF
  combined; per-line origin; PL has no G.W. total → blank + summary note);
  extended ``hailiang`` (``26HLHK01Q4010``) and ``hipus`` (PALLET + CASE units)
- ``dunan_v1`` ``parse_packing`` hook (PDF sum row / xlsx TOTAL row) + incoterm
- ``hitachi_gls_v1`` invoice no. on the line below its label (MEH6K018)
- ``bhc_my_hub_v1`` unchanged; factory PL OCR (rotated scan) TOTAL regex
- BL: ``hippopo_arrival_v1`` (N PALLETS), ``china_progress_bl_v1`` (CPSE/NBSE),
  ``tvl_hbl_v1`` SHAKEL26C… numbers, ``jif_cosmo_waybill_v1`` Ocean Links
  KLG-… waybill + HIPUS CONTAINER<6 PACKAGES>
- pairing: Chinese 发票/装箱单 filenames, glued PACKINGLIST token
"""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_extractor.checker import hard_check
from invoice_extractor.formats import bhc_vendor_ci_v1, dunan_v1
from invoice_extractor.formats.bl import (
    china_progress_bl_v1,
    hippopo_arrival_v1,
    jif_cosmo_waybill_v1,
    tvl_hbl_v1,
)
from invoice_extractor.pairing import (
    classify_role,
    parse_packing_pkg_gw,
)
from invoice_extractor.rules_engine import extract_invoice

FX = Path(__file__).resolve().parents[1] / "fixtures" / "bhc6"
PDF = "pdftotext -layout"
OCR = "ocr/tesseract"
XLSX = "excel/openpyxl"
XLS = "excel/xlrd"


def _t(name: str) -> str:
    return (FX / name).read_text(encoding="utf-8")


def _inv(fixture: str, filename: str, backend: str = PDF):
    r = extract_invoice(
        Path("/nonexistent") / filename,
        text=_t(fixture),
        backend=backend,
        needs_ocr=False,
    )
    d = r.to_dict()
    return d, hard_check(d)


def _profile(d: dict) -> str:
    return d["meta"].get("notes") or ""


# ---------------------------------------------------------------- invoices


@pytest.mark.parametrize(
    "fixture,filename,inv_no,amount,lines,qty",
    [
        ("c1_topband_inv.txt", "INVOICE-TB20260910.pdf", "TB20260910", 92158.14, 8, 2448.0),
        ("c2_topband_inv.txt", "INVOICE-TB20261004.pdf", "TB20261004", 372084.19, 7, 12960.0),
    ],
)
def test_topband_invoice(fixture, filename, inv_no, amount, lines, qty):
    d, hard = _inv(fixture, filename)
    h = d["header"]
    assert d["meta"]["format_id"] == "bhc_vendor_ci_v1"
    assert "profile=topband" in _profile(d)
    assert h["invoice_no"] == inv_no
    assert h["currency"] == "USD"
    assert h["amount"] == pytest.approx(amount)
    assert len(d["items"]) == lines
    assert h["total_quantity"] == pytest.approx(qty)
    assert h["incoterm"] == "FOB SHENZHEN"
    assert all(it["part_no"] for it in d["items"])
    assert hard["verdict"] == "pass"


@pytest.mark.parametrize(
    "fixture,pkg,gw",
    [("c1_topband_pl_xls.txt", 18.0, 3520.0), ("c2_topband_pl_xls.txt", 65.0, 12340.0)],
)
def test_topband_pl_packing(fixture, pkg, gw):
    p = bhc_vendor_ci_v1.parse_packing(_t(fixture))
    assert p["profile"] == "topband"
    assert (p["pkg"], p["gw"]) == (pkg, gw)


@pytest.mark.parametrize(
    "fixture,filename,backend",
    [
        ("c3_dunan_inv.txt", "标准_结汇发票FT00044339.pdf", PDF),
        ("c3_dunan_inv_xlsx.txt", "标准_结汇发票FT00044339.xlsx", XLSX),
    ],
)
def test_dunan_case3_invoice(fixture, filename, backend):
    d, hard = _inv(fixture, filename, backend)
    h = d["header"]
    assert d["meta"]["format_id"] == "dunan_v1"
    assert h["invoice_no"] == "DA15197958/47"
    assert h["amount"] == pytest.approx(59597.42)
    assert len(d["items"]) == 2
    assert h["total_quantity"] == pytest.approx(6140.0)
    assert h["incoterm"] == "FOB SHENZHEN"
    assert hard["verdict"] == "pass"


def test_dunan_case11_invoice():
    d, hard = _inv("c11_dunan_inv.txt", "标准_结汇发票FT00044376.pdf")
    h = d["header"]
    assert d["meta"]["format_id"] == "dunan_v1"
    assert h["invoice_no"] == "DA15199998/2/3/2/5"
    assert h["amount"] == pytest.approx(126156.46)
    assert len(d["items"]) == 8
    assert h["total_quantity"] == pytest.approx(44644.0)
    assert h["incoterm"] == "FOB NINGBO"
    assert hard["verdict"] == "pass"


@pytest.mark.parametrize(
    "fixture,pkg,gw",
    [
        ("c3_dunan_pl.txt", 35.0, 4676.0),
        ("c3_dunan_pl_xlsx.txt", 35.0, 4676.0),
        # case 11: PDF sum row above TOTAL (not the first carton row 2,764)
        ("c11_dunan_pl.txt", 34.0, 9526.0),
        ("c11_dunan_pl_xlsx.txt", 34.0, 9526.0),
    ],
)
def test_dunan_parse_packing(fixture, pkg, gw):
    p = dunan_v1.parse_packing(_t(fixture))
    assert (p["pkg"], p["gw"]) == (pkg, gw)


@pytest.mark.parametrize(
    "fixture,filename,inv_no,amount,lines,qty",
    [
        ("c4_my_hub_inv.txt", "10226901_INV_9027850165.PDF", "9027850165", 20211.6, 1, 40.0),
        ("c5_my_hub_inv.txt", "BHCWHJTV2609005_INV_9027847785.PDF", "9027847785", 146317.23, 5, 71.0),
    ],
)
def test_my_hub_unchanged(fixture, filename, inv_no, amount, lines, qty):
    d, hard = _inv(fixture, filename)
    h = d["header"]
    assert d["meta"]["format_id"] == "bhc_my_hub_v1"
    assert h["invoice_no"] == inv_no
    assert h["amount"] == pytest.approx(amount)
    assert len(d["items"]) == lines
    assert h["total_quantity"] == pytest.approx(qty)
    assert hard["verdict"] == "pass"


@pytest.mark.parametrize(
    "fixture,pkg,gw",
    [("c4_factory_pl_rotated_ocr.txt", 2.0, 786.0), ("c5_factory_pkl.txt", 71.0, 17652.0)],
)
def test_factory_pl_totals(fixture, pkg, gw):
    assert parse_packing_pkg_gw(_t(fixture)) == (pkg, gw)


def test_hisense_combined_unchanged():
    d, hard = _inv("c6_hisense.txt", "INV+PL+CIHT-TW-26090470.pdf")
    h = d["header"]
    assert d["meta"]["format_id"] == "hisense_qingdao_v1"
    assert h["invoice_no"] == "CIHT-TW-26090470"
    assert h["amount"] == pytest.approx(71400.0)
    assert (h["total_pkg"], h["gross_weight_kg"]) == (60.0, 13800.0)
    assert hard["verdict"] == "pass"


def test_hailiang_26hlhk():
    d, hard = _inv("c7_hailiang_xlsx.txt", "26HLHK01Q4010-发票箱单.xlsx", XLSX)
    h = d["header"]
    assert "profile=hailiang" in _profile(d)
    assert h["invoice_no"] == "26HLHK01Q4010"
    assert h["amount"] == pytest.approx(749014.61)
    assert len(d["items"]) == 8
    assert h["total_quantity"] == pytest.approx(49147.0)
    assert (h["total_pkg"], h["gross_weight_kg"]) == (54.0, 55064.0)
    assert h["incoterm"] == "FOB SHANGHAI"
    # description kept as printed (vendor typo REFINDED)
    assert d["items"][0]["description"].startswith("REFINDED COPPER COIL")
    assert hard["verdict"] == "pass"


def test_hitachi_meh6k018_label_next_line():
    d, hard = _inv("c8_hitachi.txt", "Shipping Docs 20261005 MEH6K018_TW.pdf")
    h = d["header"]
    assert d["meta"]["format_id"] == "hitachi_gls_v1"
    assert h["invoice_no"] == "MEH6K018"
    assert h["currency"] == "JPY"
    assert h["amount"] == pytest.approx(294030.0)
    assert [it["part_no"] for it in d["items"]] == ["P29601", "P29942"]
    assert [it["origin"] for it in d["items"]] == ["MY", "CN"]
    assert d["items"][0]["description"] == "DRAIN PAN ASSY"
    assert (h["total_pkg"], h["gross_weight_kg"]) == (1.0, 50.0)
    assert hard["verdict"] == "pass"


@pytest.mark.parametrize(
    "fixture,filename,backend",
    [("c9_hipus_inv.txt", "IV_117-BHCTW-26K-43.PDF", PDF), ("c9_hipus_inv_xlsx.txt", "IV_117-BHCTW-26K-43.xlsx", XLSX)],
)
def test_hipus_invoice(fixture, filename, backend):
    d, hard = _inv(fixture, filename, backend)
    h = d["header"]
    assert "profile=hipus" in _profile(d)
    assert h["invoice_no"] == "117-BHCTW-26K-43"
    assert h["amount"] == pytest.approx(3397361.0)
    assert len(d["items"]) == 24
    assert h["total_quantity"] == pytest.approx(8969.0)
    assert hard["verdict"] == "pass"


def test_hipus_pl_pallets_and_cases():
    p = bhc_vendor_ci_v1.parse_packing(_t("c9_hipus_pl_xlsx.txt"))
    assert (p["pkg"], p["gw"]) == (6.0, 1774.5)
    assert set(p["units"]) == {"PALLET-1", "PALLET-2", "PALLET-3", "PALLET-4", "CASE-5", "CASE-6"}


def test_saginomiya_t261565():
    d, hard = _inv("c10_saginomiya.txt", "T261565.pdf")
    h = d["header"]
    assert "profile=saginomiya" in _profile(d)
    assert h["invoice_no"] == "T261565"
    assert h["currency"] == "JPY"
    assert h["amount"] == pytest.approx(7433872.0)
    assert len(d["items"]) == 25
    assert h["total_quantity"] == pytest.approx(9854.0)
    assert h["total_pkg"] == 5.0
    # Total row 1,221.46 is Net Weight → G.W. blank + soft summary note
    assert h["gross_weight_kg"] is None
    assert "Net Weight" in (h.get("summary_note") or "")
    assert h["incoterm"] == "FOB YOKOHAMA"
    assert {it["origin"] for it in d["items"]} == {"China", "Japan"}
    assert hard["verdict"] == "pass"


@pytest.mark.parametrize(
    "fixture,filename,inv_no,amount,lines,qty,incoterm,pkg,gw",
    [
        ("c12_augewei_inv.txt", "INV TW AGW202609300001.pdf", "AGW202609300001", 26755.2, 2, 12960.0,
         "FOB SHANGHAI", 20.0, 8690.4),
        ("c13_jiangnan_inv.txt", "COMMERCIAL INVOICE-JCN26589.pdf", "JCN26589", 16170.0, 2, 4000.0,
         "FOB SHANGHAI", 5.0, 3000.0),
    ],
)
def test_augewei_jiangnan(fixture, filename, inv_no, amount, lines, qty, incoterm, pkg, gw):
    d, hard = _inv(fixture, filename)
    h = d["header"]
    assert h["invoice_no"] == inv_no
    assert h["amount"] == pytest.approx(amount)
    assert len(d["items"]) == lines
    assert h["total_quantity"] == pytest.approx(qty)
    assert h["incoterm"] == incoterm
    assert hard["verdict"] == "pass"
    pl = fixture.replace("_inv.txt", "_pl.txt")
    p = bhc_vendor_ci_v1.parse_packing(_t(pl))
    assert (p["pkg"], p["gw"]) == (pkg, gw)


def test_jiangnan_htsus_and_blank_origin():
    d, _ = _inv("c13_jiangnan_inv.txt", "COMMERCIAL INVOICE-JCN26589.pdf")
    assert "profile=jiangnan" in _profile(d)
    assert all(it["hs_code"] == "8482990000" for it in d["items"])
    assert all(not it["origin"] for it in d["items"])
    assert "origin blank" in _profile(d)


def test_wolong_vn_numeric_total():
    d, hard = _inv("c14_wolong_xlsx.txt", "WLVN26501.xlsx", XLSX)
    h = d["header"]
    assert "profile=wolong" in _profile(d)
    assert h["invoice_no"] == "WLVN26501"
    assert h["amount"] == pytest.approx(45113.58)
    assert len(d["items"]) == 3
    assert h["total_quantity"] == pytest.approx(2058.0)
    assert (h["total_pkg"], h["gross_weight_kg"]) == (12.0, 5045.56)
    assert h["incoterm"] == "FOB HAIPHONG"
    assert all(it["hs_code"] == "85013130" for it in d["items"])
    assert all(it["origin"] == "Viet Nam" for it in d["items"])
    assert "does not match the numeric TOTAL" in _profile(d)
    assert hard["verdict"] == "pass"


def test_wolong_cn_xls_numeric_total():
    d, hard = _inv("c15_wolong_xls.txt", "WLA26322-3 台湾博世 海运拼箱9.21.xls", XLS)
    h = d["header"]
    assert "profile=wolong" in _profile(d)
    assert h["invoice_no"] == "WLA26322-3"
    assert h["amount"] == pytest.approx(8652.0)
    assert len(d["items"]) == 2  # 3 zero template rows skipped
    assert h["total_quantity"] == pytest.approx(480.0)
    assert (h["total_pkg"], h["gross_weight_kg"]) == (4.0, 1841.6)
    assert h["incoterm"] == "FOB"
    assert all(it["hs_code"] == "8501310090" for it in d["items"])
    assert "does not match the numeric TOTAL" in _profile(d)
    assert "template row" in _profile(d)
    assert hard["verdict"] == "pass"


# ---------------------------------------------------------------- BL


@pytest.mark.parametrize(
    "mod,fixture,filename,bl_no,pkg,gw",
    [
        (hippopo_arrival_v1, "c1_hippopo_arrival.txt", "到貨通知.pdf", "CPSE26090433", 18.0, 3520.0),
        (hippopo_arrival_v1, "c14_hippopo_arrival.txt", "到貨通知.pdf", "P043ADNE2609", 12.0, 5045.56),
        (hippopo_arrival_v1, "c15_hippopo_arrival.txt", "到貨通知.pdf", "SHSE26090288", 4.0, 1841.6),
        (china_progress_bl_v1, "c3_china_progress_bl.txt", "44339提单.pdf", "CPSE26090321", 35.0, 4676.0),
        (china_progress_bl_v1, "c11_china_progress_bl.txt", "44376提单.pdf", "NBSE26090062", 34.0, 9526.0),
    ],
)
def test_text_bl(mod, fixture, filename, bl_no, pkg, gw):
    text = _t(fixture)
    assert mod.match_score(text, filename) >= 0.5
    r = mod.extract(f"/nonexistent/{filename}", text, PDF, False).to_dict()
    h = r["header"]
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == (bl_no, pkg, gw)
    assert not r["meta"].get("needs_gold_fields")


def test_tvl_shakel_c_bl_numbers():
    v = tvl_hbl_v1._read_votes(_t("c13_tvl_hbl_ocr.txt"))
    assert v["bl_no"] == "SHAKEL26C71898"
    assert v["face_gw"] == pytest.approx(3000.0)
    assert ("say_words", 5.0) in v["say"]
    # synthetic: full C-number after the B/L NO. label is kept (not truncated)
    assert tvl_hbl_v1._read_votes("B/L NO. SHAKEL26C72175\n")["bl_no"] == "SHAKEL26C72175"
    assert tvl_hbl_v1._TOK_BL_RX.search("SHAKEL26C72175")
    # phantom digit after C (C read as C + glyph) is normalised away
    assert tvl_hbl_v1._SHAKEL_C_PHANTOM.sub(r"SHAKEL\1C\2", "SHAKEL26C072175") == "SHAKEL26C72175"


def test_tvl_numeric_bl_unchanged():
    assert tvl_hbl_v1._read_votes(_t("c7_tvl_hbl_ocr.txt"))["bl_no"] == "SHAKEL26971215"
    assert tvl_hbl_v1._read_votes(_t("c5_tvl_hbl_ocr.txt"))["bl_no"] == "SHAKEL26971972"


def test_jif_ocean_links_waybill():
    text = _t("c10_ocean_links_waybill_ocr.txt")
    assert jif_cosmo_waybill_v1.match_score(text, "20260929202543-0001.pdf") >= 0.5
    assert jif_cosmo_waybill_v1._bl_nos(text) == ["KLG-T268Y98"]
    pk, gw, _ = jif_cosmo_waybill_v1._pass_reads(text, "t")
    assert {v for _, v in pk} == {5.0}
    assert {v for _, v in gw} == {1460.9}


def test_jif_kee_waybills():
    assert jif_cosmo_waybill_v1._bl_nos(_t("c9_jif_waybill_ocr.txt")) == ["261002KEE101"]
    # case8: the forwarder's ORIGINAL 3-page scan (KEE601 face + marks sheet, KEE602 face)
    pages = _t("c8_jif_waybill_3page_ocr.txt").split("\f")
    assert len(pages) == 3
    assert jif_cosmo_waybill_v1._bl_nos(pages[2]) == ["261002KEE602"]
    pk, gw, _ = jif_cosmo_waybill_v1._pass_reads(pages[2], "t")
    assert {v for _, v in pk} == {1.0}
    # G.W. 50.000 sits under the watermark hatch — the page pass has no read
    # (the located cell re-read on the real scan reads it, see test below)
    assert gw == []


def test_jif_vote_needs_two_reads():
    v, ok, _ = jif_cosmo_waybill_v1._vote([("a", 50.0)])
    assert not ok


# ---------------------------------------------------------------- pairing


@pytest.mark.parametrize(
    "filename,fixture,role",
    [
        ("标准_结汇发票FT00044339.pdf", "c3_dunan_inv.txt", "inv"),
        ("标准_结汇装箱单FT00044339.pdf", "c3_dunan_pl.txt", "pkl"),
        ("PACKINGLIST-TB20260910.xls", "c1_topband_pl_xls.txt", "pkl"),
        ("INVOICE-TB20260910.pdf", "c1_topband_inv.txt", "inv"),
        ("COMMERCIAL INVOICE-JCN26589.pdf", "c13_jiangnan_inv.txt", "inv"),
        ("PACKING LIST-JCN26589.pdf", "c13_jiangnan_pl.txt", "pkl"),
        ("10226901_PL.pdf", "c4_factory_pl_rotated_ocr.txt", "pkl"),
        ("T261565.pdf", "c10_saginomiya.txt", "combined"),
        ("20260929202543-0001.pdf", "c10_ocean_links_waybill_ocr.txt", "bl"),
        ("44376提单.pdf", "c11_china_progress_bl.txt", "bl"),
    ],
)
def test_roles(filename, fixture, role):
    assert classify_role(Path(filename), _t(fixture)).role == role


def test_glued_packinglist_token_only_without_invoice():
    assert classify_role(Path("PACKINGLIST-TB20261004.xls"), filename_only=True).role == "pkl"
    # BHC 5th case3 file keeps its text-led role (not a PKL-only row)
    r = classify_role(Path("TAWA-26024(260921)Invoice & Packinglist.pdf"), filename_only=True)
    assert r.role != "pkl"
    assert classify_role(Path("26HLHK01Q4010-发票箱单.xlsx"), filename_only=True).role == "combined"


def test_my_hub_xlsx_twin_pn_split():
    """xlsx twin keeps PDF column gaps in one cell → PN 'RAM-18GSD C' (= PDF row)."""
    d, hard = _inv("c5_my_hub_inv_xlsx.txt", "BHCWHJTV2609005_INV_9027847785.xlsx", XLSX)
    pdf, _ = _inv("c5_my_hub_inv.txt", "BHCWHJTV2609005_INV_9027847785.PDF")
    assert d["meta"]["format_id"] == "bhc_my_hub_v1"
    assert [(i["part_no"], i["description"]) for i in d["items"]] == [
        (i["part_no"], i["description"]) for i in pdf["items"]
    ]
    assert d["items"][0]["part_no"] == "RAM-18GSD C"
    assert d["items"][0]["description"] == "SF RAM,RAS"
    assert hard["verdict"] == "pass"


def test_hipus_xlsx_twin_cambodia_origin():
    d, _ = _inv("c9_hipus_inv_xlsx.txt", "IV_117-BHCTW-26K-43.xlsx", XLSX)
    pdf, _ = _inv("c9_hipus_inv.txt", "IV_117-BHCTW-26K-43.PDF")
    assert [i["origin"] for i in d["items"]] == [i["origin"] for i in pdf["items"]]
    assert "Cambodia" in {i["origin"] for i in d["items"]}


# ---------------------------------------------------------------- Auditor round 2 (case8 multi-waybill)

C8_DIR = Path("/home/box/Downloads/BHC-batch-6th/BHC_6th data/case8/run")
C8_BL = C8_DIR / "20261002094338-0001.pdf"


def test_jif_gw_cell_parse():
    g = jif_cosmo_waybill_v1._gw_cell
    assert g("50.000") == 50.0
    assert g("2..50.000") == 50.0  # hatch fragments in front
    assert g("50.0005") == 50.0  # one trailing hatch digit
    assert g(".50,000") == 50.0
    assert g("1,774.500") == pytest.approx(1774.5)
    assert g("0.000") is None and g("50") is None and g("22.50.00") is None


def test_jif_component_vote():
    v = jif_cosmo_waybill_v1._component_vote
    reads = [(50, 0.006)] * 4 + [(50, 0.0)] * 5 + [(40, 0.0)] * 3
    assert v(reads) == (50.0, 8)
    assert v([(745, 0.0), (748, 0.0)]) == (None, 0)  # no majority → not used
    assert v([]) == (None, 0)


def test_jif_waybill_groups_3page():
    text = _t("c8_jif_waybill_3page_ocr.txt")
    assert jif_cosmo_waybill_v1._waybill_groups(text) == [(0, [0, 1]), (2, [2])]
    assert jif_cosmo_waybill_v1._waybill_groups("Gross Weight 1\fmarks") == [(0, [0, 1])]


def test_jif_multi_waybill_header_blank_and_documents():
    r = jif_cosmo_waybill_v1.extract(
        "/nonexistent/20261002094338-0001.pdf", _t("c8_jif_waybill_3page_ocr.txt"), OCR, True
    ).to_dict()
    h, m = r["header"], r["meta"]
    assert h["bl_no"] is None and h["packages"] is None and h["gross_weight_kg"] is None
    assert set(m["needs_gold_fields"]) == {"bl_no", "packages", "gross_weight_kg"}
    docs = m["documents"]
    assert [d["bl_no"] for d in docs] == ["261002KEE601", "261002KEE602"]
    assert [d["pages"] for d in docs] == [[1, 2], [3]]


def _two_docs(reads601, reads602):
    return {
        "header": {"bl_no": None, "packages": None, "gross_weight_kg": None},
        "meta": {
            "needs_gold": True,
            "needs_gold_fields": ["bl_no", "packages", "gross_weight_kg"],
            "documents": [
                {"pages": [1, 2], "bl_no": "261002KEE601", "packages": 5.0, "gross_weight_kg": 745.0,
                 "needs_gold_fields": ["packages"], "invoice_reads": reads601, "notes": ""},
                {"pages": [3], "bl_no": "261002KEE602", "packages": 1.0, "gross_weight_kg": 50.0,
                 "needs_gold_fields": [], "invoice_reads": reads602, "notes": ""},
            ],
        },
    }


def test_select_bl_document_by_invoice_no():
    from invoice_extractor.pairing import select_bl_document

    bl = _two_docs(["MEH6KO19", "MEHGKO19", "MEHGKOT9"], ["MEH6KO18", "MEH6K018", "MEHGK018"])
    s = select_bl_document(bl, "MEH6K018")
    assert (s["header"]["bl_no"], s["header"]["packages"], s["header"]["gross_weight_kg"]) == (
        "261002KEE602", 1.0, 50.0)
    assert not s["meta"]["needs_gold"] and not s["meta"]["needs_gold_fields"]
    assert "261002KEE601" in s["meta"]["selected_waybill"]  # unused waybill named
    # the other invoice picks the other waybill (its own field flags carried over)
    s2 = select_bl_document(bl, "MEH6K019")
    assert s2["header"]["bl_no"] == "261002KEE601" and s2["meta"]["needs_gold_fields"] == ["packages"]
    # no match → nothing guessed
    s3 = select_bl_document(bl, "MEH6K020")
    assert s3["header"]["bl_no"] is None and s3["header"]["gross_weight_kg"] is None
    assert set(s3["meta"]["needs_gold_fields"]) == {"bl_no", "packages", "gross_weight_kg"}
    # a single matching read is not enough; matches on two documents → ambiguous
    assert select_bl_document(_two_docs([], ["MEH6K018"]), "MEH6K018")["header"]["bl_no"] is None
    amb = _two_docs(["MEH6K018", "MEH6K018"], ["MEH6K018", "MEH6K018"])
    assert select_bl_document(amb, "MEH6K018")["header"]["bl_no"] is None
    # single-document BLs pass through untouched
    one = {"header": {"bl_no": "X"}, "meta": {}}
    assert select_bl_document(one, "MEH6K018") is one


def test_merge_flags_unmatched_multi_waybill():
    from invoice_extractor.pairing import merge_bl_onto_inv, select_bl_document

    inv = extract_invoice(Path("/nonexistent/Shipping Docs 20261005 MEH6K018_TW.pdf"),
                          text=_t("c8_hitachi.txt"), backend=PDF, needs_ocr=False)
    s = select_bl_document(_two_docs(["MEH6KO19"] * 3, ["MEH6KO20"] * 3), "MEH6K018")
    out = merge_bl_onto_inv(inv, bl_header=s["header"], bl_path="x.pdf", bl_meta=s["meta"]).to_dict()
    assert out["header"]["bl_no"] is None
    assert {"bl_no", "bl_packages", "bl_gross_weight_kg"} <= set(out["meta"]["needs_gold_fields"])


def test_line_run_extends_over_value():
    from invoice_extractor.ocr_reread import Word, line_run

    ws = [Word("INVOICE", 100, 10, 130, 18, (1,)), Word("NO.", 132, 10, 145, 18, (1,)),
          Word("MEH6K018", 150, 10, 190, 18, (1,)), Word("far", 400, 10, 420, 18, (1,))]
    assert line_run(ws, (100, 10, 145, 18), max_gap=20, max_width=150) == (100, 10, 190, 18)


@pytest.mark.skipif(not C8_BL.is_file(), reason="BHC 6th case8 scan not on this machine")
def test_case8_original_3page_scan_end_to_end():
    from invoice_extractor.pairing import auto_pair, extract_pair_row

    from invoice_extractor.pairing import dedupe_shared_packing_units

    rows = auto_pair(sorted(C8_DIR.glob("*.pdf")))
    assert len(rows) == 1
    d = extract_pair_row(rows[0])
    # G.W. 50 is a cell-only read: flagged per row, accepted by the batch step
    # because it equals the INV/PL G.W. total of the waybill's invoices (50)
    assert d["meta"]["needs_gold_fields"] == ["bl_gross_weight_kg"]
    dedupe_shared_packing_units([d])
    h = d["header"]
    assert (h["invoice_no"], h["bl_no"], h["bl_packages"], h["bl_gross_weight_kg"]) == (
        "MEH6K018", "261002KEE602", 1.0, 50.0)
    assert not d["meta"].get("needs_gold_fields") and d["_hard"]["verdict"] == "pass"
    assert "261002KEE601" in d["meta"]["notes"]  # unused waybill named in the notes
    assert "INV/PL G.W. total 50" in d["meta"]["notes"]


def test_tvl_phantom_digit_only_stripped_when_page_pass_supports_it():
    f = tvl_hbl_v1._phantom_fix
    assert f("SHAKEL26C072175", ["SHAKEL26072175"]) == "SHAKEL26C72175"
    assert f("SHAKEL26C072175", ["SHAKEL26C72175"]) == "SHAKEL26C72175"
    # genuine 6-digit C number: page pass also reads 6 digits → kept
    assert f("SHAKEL26C072175", ["SHAKEL26C072175"]) == "SHAKEL26C072175"
    assert f("SHAKEL26C072175", []) == "SHAKEL26C072175"
    assert f("SHAKEL26C72175", []) == "SHAKEL26C72175"
    assert tvl_hbl_v1._read_votes("B/L NO. SHAKEL26C072175\n")["bl_no"] == "SHAKEL26C072175"


def test_saginomiya_filename_hint_is_anchored():
    t = _t("c10_saginomiya.txt")
    assert bhc_vendor_ci_v1.match_score(t, "T261565.pdf") > bhc_vendor_ci_v1.match_score(t, "XT261565.pdf")


# ---------------------------------------------------------------- Auditor round 3/4 (GW decision)
# Round 4 (conservative): one vote per independent source (page pass r1, clean
# pass, token clip); a confirmed cell is one more source, an unconfirmed cell
# never votes; confident only when ≥2 voting sources all agree. A cell-only G.W.
# is accepted only when it equals the INV/PL G.W. total of the waybill's invoices.

_dec = jif_cosmo_waybill_v1._decide_gw


def _cell(v, confirmed):
    return {"value": v, "verified": confirmed}


def test_gw_true50_two_misread150_is_needs_gold():
    g, ok, _, note, _ = _dec([("r1", 150.0), ("clean", 150.0)], _cell(50.0, True))
    assert not ok and "needs_gold" in note
    g, ok, _, _, _ = _dec([("r1", 150.0), ("clean", 150.0)], _cell(50.0, False))
    assert not ok  # an unconfirmed cell cannot decide, but it blocks


def test_gw_single_misread150_vs_confirmed_50_is_needs_gold():
    g, ok, _, _, _ = _dec([("r1", 150.0)], _cell(50.0, True))
    assert not ok


@pytest.mark.parametrize("cut,full", [(1.774, 1774.5), (3.084, 3084.5)])  # right cut (decimals lost)
def test_gw_right_cut_unconfirmed_cell_vs_one_page_read_is_needs_gold(cut, full):
    g, ok, detail, note, _ = _dec([("r1", full)], _cell(cut, False))
    assert not ok and "unconfirmed" in detail and "needs_gold" in note


@pytest.mark.parametrize("cut,full", [(774.5, 1774.5), (84.5, 3084.5), (1.774, 1774.5), (3.084, 3084.5)])
def test_gw_unconfirmed_cell_disagreeing_blocks(cut, full):
    # left cut (prefix lost) and right cut (decimals lost): never decides, and
    # disagreeing with the page/token reads → needs_gold even when they agree
    g, ok, _, note, _ = _dec([("clean", full), ("tok", full)], _cell(cut, False))
    assert g == full and not ok and "disagrees" in note
    # agreeing unconfirmed cell does not count towards the ≥2
    assert _dec([("r1", full)], _cell(full, False))[1] is False
    assert _dec([("r1", full), ("tok", full)], _cell(full, False))[:2] == (full, True)


def test_gw_token_rereads_are_one_source():
    # 4998 misread at all 3 dpi of one token clip = ONE vote; vs confirmed cell 1998 → needs_gold
    tok = jif_cosmo_waybill_v1._source_value([4998.0, 4998.0, 4998.0])
    assert tok == 4998.0
    g, ok, _, _, _ = _dec([("r1", None), ("clean", None), ("tok", tok)], _cell(1998.0, True))
    assert not ok
    assert jif_cosmo_waybill_v1._source_value([1998.0, 4998.0]) is None  # no majority → abstains


def test_gw_any_disagreement_between_sources_is_needs_gold():
    assert _dec([("r1", 1998.0), ("clean", 1998.0), ("tok", 4998.0)], None)[1] is False
    assert _dec([("r1", 1998.0), ("clean", 1998.0), ("tok", 1998.0)], None)[:2] == (1998.0, True)


@pytest.mark.parametrize("cut", [774.5, 1.774, 50.0])
@pytest.mark.parametrize("confirmed", [False, True])
def test_gw_cell_only_is_never_decided_by_the_bl(cut, confirmed):
    # left cut / right cut / whole: with no page or token source the BL alone
    # never accepts the cell (widened-box confirmation is not enough)
    g, ok, _, note, cell_only = _dec([("r1", None), ("tok", None)], _cell(cut, confirmed))
    assert not ok and cell_only == cut and "cell re-read only" in note


def _row(inv, gw, cell=None, bl_file="/x/BL.pdf", bl_no="261002KEE602"):
    flds = ["bl_gross_weight_kg"] if cell is not None else None
    m = {"bl_file": bl_file, "needs_gold_fields": flds, "needs_gold": bool(flds), "notes": "", "confidence": "rules"}
    if cell is not None:
        m["bl_gw_cell_only"] = {"value": cell, "inv_needs_gold": False}
    return {"header": {"invoice_no": inv, "gross_weight_kg": gw, "bl_no": bl_no, "bl_gross_weight_kg": cell,
                       "amount": None},
            "items": [], "meta": m}


def test_cell_only_gw_corroborated_by_shipment_total_only():
    from invoice_extractor.pairing import corroborate_cell_only_gw

    one = [_row("MEH6K018", 50.0, cell=50.0)]
    corroborate_cell_only_gw(one)
    assert not one[0]["meta"]["needs_gold_fields"] and "INV/PL G.W. total 50" in one[0]["meta"]["notes"]
    # invoices A 774.5 + B 1,000 on one waybill (total 1,774.5): a left-cut cell 774.5 is NOT corroborated
    ab = [_row("A", 774.5, cell=774.5), _row("B", 1000.0, cell=774.5)]
    corroborate_cell_only_gw(ab)
    assert all(r["meta"]["needs_gold_fields"] == ["bl_gross_weight_kg"] for r in ab)
    # the full value equals the total → accepted on both rows
    ab = [_row("A", 774.5, cell=1774.5), _row("B", 1000.0, cell=1774.5)]
    corroborate_cell_only_gw(ab)
    assert all(not r["meta"]["needs_gold_fields"] for r in ab)
    # PDF + xlsx twins of one invoice count once (one twin blank: single shared PL)
    tw = [_row("X", 1774.5, cell=1774.5), _row("X", None, cell=1774.5)]
    corroborate_cell_only_gw(tw)
    assert all(not r["meta"]["needs_gold_fields"] for r in tw)
    # an invoice without G.W. → no total → stays flagged; right-cut 1.774 never matches
    for rows in ([_row("A", None, cell=774.5), _row("B", 1000.0, cell=774.5)], [_row("X", 1774.5, cell=1.774)]):
        corroborate_cell_only_gw(rows)
        assert all(r["meta"]["needs_gold_fields"] == ["bl_gross_weight_kg"] for r in rows)
    # rows on another waybill don't count
    other = [_row("A", 50.0, cell=50.0), _row("B", 70.0, bl_file="/x/OTHER.pdf")]
    corroborate_cell_only_gw(other)
    assert not other[0]["meta"]["needs_gold_fields"]


def test_select_note_single_matching_read_says_too_few():
    from invoice_extractor.pairing import select_bl_document

    s = select_bl_document(_two_docs([], ["MEH6K018"]), "MEH6K018")
    assert s["header"]["bl_no"] is None
    assert "too few matching INVOICE NO. reads" in s["meta"]["notes"]


def test_select_requires_exact_invoice_no_after_folding():
    from invoice_extractor.pairing import select_bl_document

    bl = _two_docs(["A12345", "A12345", "A1Z345"], ["XYZ999", "XYZ999"])
    s = select_bl_document(bl, "A1234")  # invoice A1234 must not take A12345's waybill
    assert s["header"]["bl_no"] is None
    assert "none has a printed INVOICE NO. matching A1234" in s["meta"]["notes"]
    assert select_bl_document(bl, "A12345")["header"]["bl_no"] == "261002KEE601"  # Z→2 folding still applies


def test_select_note_when_more_than_one_waybill_matches():
    from invoice_extractor.pairing import select_bl_document

    amb = _two_docs(["MEH6K018", "MEH6K018"], ["MEH6KO18", "MEH6K018"])
    s = select_bl_document(amb, "MEH6K018")
    assert s["header"]["bl_no"] is None and s["meta"]["needs_gold"] is True
    assert "matched more than one waybill" in s["meta"]["notes"]


def test_merge_sets_row_needs_gold_when_bl_fields_flagged():
    from invoice_extractor.pairing import merge_bl_onto_inv, select_bl_document

    inv = extract_invoice(Path("/nonexistent/Shipping Docs 20261005 MEH6K018_TW.pdf"),
                          text=_t("c8_hitachi.txt"), backend=PDF, needs_ocr=False)
    s = select_bl_document(_two_docs(["MEH6KO19"] * 3, ["MEH6KO20"] * 3), "MEH6K018")
    out = merge_bl_onto_inv(inv, bl_header=s["header"], bl_path="x.pdf", bl_meta=s["meta"]).to_dict()
    assert out["meta"]["needs_gold"] is True


C9_BL = Path("/home/box/Downloads/BHC-batch-6th/BHC_6th data/case9/run/WAYBILL.pdf")
B4C8_BL = Path("/home/box/Downloads/BHC-batch-4th/BHC_4th data/case 8/WAYBILL.pdf")


B4C6_BL = Path("/home/box/Downloads/BHC-batch-4th/BHC_4th data/case 6/BL.pdf")


@pytest.mark.parametrize("path,bl_no,pkg,gw", [
    (B4C8_BL, "260918KEE102", 10.0, 3084.5),
    (B4C6_BL, "260918KEE103", 16.0, 1998.0),
])
def test_jif_real_scan_gw_with_cell_reread(path, bl_no, pkg, gw):
    if not path.is_file():
        pytest.skip("scan not on this machine")
    from invoice_extractor.bl_rules_engine import extract_bl

    d = extract_bl(path).to_dict()
    h = d["header"]
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == (bl_no, pkg, gw)
    assert not d["meta"].get("needs_gold_fields")


def test_case9_waybill_gw_needs_gold_when_cell_disagrees():
    """Round 4 honest result: page + token read 1,774.5, but the cell re-read
    (box lost the leading ``1,``) reads 774.5 11/12 → sources disagree →
    needs_gold with 1,774.5 kept as the suggestion."""
    if not C9_BL.is_file():
        pytest.skip("scan not on this machine")
    from invoice_extractor.bl_rules_engine import extract_bl

    d = extract_bl(C9_BL).to_dict()
    h, m = d["header"], d["meta"]
    assert (h["bl_no"], h["packages"], h["gross_weight_kg"]) == ("261002KEE101", 6.0, 1774.5)
    assert m["needs_gold_fields"] == ["gross_weight_kg"]
    assert "disagrees" in m["notes"]
