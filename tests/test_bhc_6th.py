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
    text8 = _t("c8_jif_waybill_ocr.txt")
    assert jif_cosmo_waybill_v1._bl_nos(text8) == ["261002KEE602"]
    pk, gw, _ = jif_cosmo_waybill_v1._pass_reads(text8, "t")
    assert {v for _, v in pk} == {1.0}
    # G.W. 50.000 sits under the watermark hatch — no text read → needs_gold
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
