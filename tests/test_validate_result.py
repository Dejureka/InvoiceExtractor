"""Validator rules, Excel exports and the two historical false passes."""
from copy import deepcopy
from pathlib import Path
import sys

from openpyxl import load_workbook
import pytest

from invoice_extractor.export import write_xlsx_many

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from validate_result import main, read_extracts, validate

FIXTURES = ROOT / "fixtures/validate_prefix"


@pytest.fixture
def invoice():
    return {
        "header": {
            "invoice_no": "00012345", "invoice_date": "2026-10-09", "currency": "EUR",
            "amount": 10.25, "total_pkg": 2, "gross_weight_kg": 25, "item_line_count": 1,
        },
        "items": [{
            "part_no": "ABC-123", "qty": 1, "unit_price": 10.25, "amount": 10.25,
            "hs_code": "01234567", "item_no": 1,
        }],
        "meta": {"format_id": "pt_gloria_v1", "labeled_amount": 10.25},
    }


def findings(invoice, rule):
    return [f for f in validate(extracts=invoice).findings if f.rule_id == rule]


@pytest.mark.parametrize("section, field, value, rule", [
    *(("header", key, None, "H_HDR_MISSING") for key in (
        "invoice_no", "invoice_date", "currency", "amount", "total_pkg", "gross_weight_kg",
    )),
    ("header", "invoice_date", "2026-02-30", "H_DATE"),
    ("header", "currency", "ABC", "H_CURRENCY"),
    ("header", "total_pkg", 1.5, "H_PKG_INTEGER"),
    ("header", "total_pkg", -1, "H_PKG_INTEGER"),
    ("header", "total_pkg", 0, "H_HDR_MISSING"),
    ("header", "item_line_count", 3, "H_LINE_COUNT"),
    *(("items", key, None, "H_LINE_MISSING") for key in ("part_no", "qty", "amount")),
    ("items", "unit_price", 10.28, "H_LINE_MATH"),
    ("items", "pricing_unit", 0, "H_PRICING_UNIT"),
    ("items", "item_no", 3, "H_LINE_POS"),
    ("items", "hs_code", None, "H_HS_MISSING"),
    ("items", "hs_code", "0101.A100", "H_HS_FORMAT"),
    ("items", "hs_code", "012345678", "H_HS_FORMAT"),
    ("meta", "labeled_amount", 12, "H_PRINTED_AMOUNT"),
    ("meta", "printed_pkg", 3, "H_PRINTED_PACKING"),
    ("meta", "printed_gw", 26, "H_PRINTED_PACKING"),
    ("meta", "total_nw", 25, "H_GW_NW"),
    ("meta", "total_nw", 26, "H_GW_NW"),
    ("meta", "vendor_typo", True, "H_VENDOR_TOTAL_NOTE"),
])
def test_hard_rules(invoice, section, field, value, rule):
    destination = invoice[section][0] if section == "items" else invoice[section]
    destination[field] = value
    assert any(f.status == "hard" for f in findings(invoice, rule))


def test_printed_total_needs_independent_evidence(invoice):
    assert not validate(extracts=invoice).findings
    invoice["meta"].update(labeled_amount=44, labeled_amount_label="sum(lines)")
    assert not findings(invoice, "H_PRINTED_AMOUNT")
    invoice["meta"].update(printed_amount=72, vendor_typo=True, notes="vendor typo: printed total 72")
    assert [f.status for f in findings(invoice, "W_VENDOR_TOTAL")] == ["warn"]
    invoice["meta"]["notes"] = "vendor typo: sum(lines) 10.25 used"
    assert [f.status for f in findings(invoice, "H_VENDOR_TOTAL_NOTE")] == ["hard"]


def test_positions_and_pricing_units(invoice):
    line = invoice["items"][0]
    line.update(qty=100, pricing_unit=100, item_no=10, hs_code="0123.4567.89")
    invoice["items"].append(dict(line, item_no=20))
    invoice["header"].update(item_line_count=2, amount=20.5)
    invoice["meta"]["labeled_amount"] = 20.5
    assert not validate(extracts=invoice).findings
    invoice["items"][1]["item_no"] = 10
    assert findings(invoice, "H_LINE_POS")
    invoice["items"][1]["item_no"] = 30
    assert findings(invoice, "H_LINE_POS")


def test_warnings_and_needs_gold(invoice):
    invoice["meta"].update(format_id="bhc_vendor_ci_v1", needs_gold=True,
                           needs_gold_fields=["header.total_pkg"], watermark="NOT VALID")
    invoice["header"]["total_pkg"] = None
    invoice["items"][0].update(hs_code=None, unit_price=10.26)
    report = validate(extracts=invoice)
    # Line diff 0.01 is within the Auditor 2026-11-20 line tolerance -> ok, no W_ROUNDING.
    assert {f.rule_id for f in report.findings} == {
        "H_HDR_MISSING", "W_HS_MISSING", "W_WATERMARK",
    }
    assert report.counts == {"ok": 0, "warn": 3, "hard": 0}
    assert "needs_gold" in findings(invoice, "H_HDR_MISSING")[0].note
    invoice["items"][0]["hs_code"] = "bad"
    invoice["meta"]["needs_gold_fields"] = ["items.hs_code"]
    assert findings(invoice, "H_HS_FORMAT")[0].status == "warn"


def test_ebike(invoice):
    invoice["items"][0].update(qty=3, unit_price=3.416667, net_weight=11, hs_code=None)
    invoice["meta"].update(format_id="ebike_ax_billing_v1", total_nw=10)
    report = validate(extracts=invoice)
    assert {f.rule_id for f in report.findings} == {"W_LINE_NW", "W_DUAL_CURRENCY", "W_HS_MISSING"}
    invoice["items"][0]["unit_price"] = 3.41667
    assert findings(invoice, "H_LINE_MATH")
    invoice["header"].update(total_pkg=0, gross_weight_kg=0,
                             summary_note="shipment pkg/GW (deduped) on 123; printed pkg/GW 1 / 10")
    assert len(findings(invoice, "H_HDR_MISSING")) == 2


@pytest.mark.parametrize("format_id", ["ma_with_period_v1", "bhc_vendor_ci_v1"])
def test_shipment_first_and_bl(invoice, format_id):
    invoice["meta"]["format_id"] = format_id
    invoice["header"].update(bl_no="BL-1", bl_packages=2, bl_gross_weight_kg=25)
    twin = deepcopy(invoice)
    twin["header"].update(invoice_no="124", total_pkg=0, gross_weight_kg=0)
    assert len(findings(twin, "H_HDR_MISSING")) == 2
    twin["header"]["summary_note"] = "shipment pkg/GW (deduped) on 00012345; printed pkg/GW 1 / 10"
    assert validate(extracts=[invoice, twin]).counts["hard"] == 0
    twin["header"]["bl_gross_weight_kg"] = 20
    assert findings([invoice, twin], "H_BL_TOTAL_CONFLICT")
    twin["header"]["bl_gross_weight_kg"] = 25
    invoice["header"]["gross_weight_kg"] = 24
    assert [f.field for f in findings([invoice, twin], "H_BL_TOTAL")] == ["bl_gross_weight_kg"]


def test_explicit_bill_and_duplicates(invoice):
    bill = {"header": {"hbl_no": "BL-1", "invoice_refs": [invoice["header"]["invoice_no"]], "packages": 4}}
    assert validate(extracts=invoice, bl_extracts=bill).findings[0].rule_id == "H_BL_TOTAL"
    assert len(findings([invoice, invoice], "H_DUPLICATE")) == 2


def test_workbook_cell_types_and_precision(invoice, tmp_path):
    invoice["items"][0].update(qty=3, unit_price=3.416667)
    invoice["meta"]["format_id"] = "ebike_ax_billing_v1"
    path = tmp_path / "Result.xlsx"
    write_xlsx_many([invoice], path)
    assert validate(path).counts["hard"] == 0
    assert validate(path, invoice).counts["hard"] == 0
    wb = load_workbook(path)
    for sheet, cell, value in (
        ("Summary", "A2", 12345),
        ("Summary", "B2", "2"),
        ("Lines", "D2", 3.41667),
        ("Lines", "H2", "1.23E+6"),
        ("Lines", "C2", "=3"),
    ):
        wb[sheet][cell] = value
    wb.save(path)
    report = validate(path, invoice)
    assert {f.row for f in report.findings if f.rule_id == "H_XLSX_DIFF"} == {
        "Summary!A2", "Summary!B2", "Lines!D2", "Lines!H2", "Lines!C2",
    }
    assert validate(path).counts["hard"] > 0
    report_path = tmp_path / "findings.xlsx"
    report.write(report_path)
    assert load_workbook(report_path).sheetnames == ["Findings", "Summary"]
    assert main([str(path), "--out", str(tmp_path / "findings.md")]) == 1
    assert validate(path, invoice, format_filter="ma_no_period_v1").counts["hard"] == 0


def test_pdf_anchor(invoice, tmp_path):
    import fitz

    path = tmp_path / "source.pdf"
    with fitz.open() as doc:
        doc.new_page()
        doc.new_page().insert_text((72, 72), "ABC-123")
        doc.save(path)
    invoice["meta"]["source_file"] = str(path)
    invoice["items"][0]["hs_code"] = None
    hit = findings(invoice, "H_HS_MISSING")[0]
    assert hit.page == 2 and hit.position.startswith("(") and hit.row == 1


def check_prefix(ma, pt):
    assert all(data["meta"]["checker_verdict"] == "pass" for data in [ma, *pt])
    assert [(f.row, f.status) for f in findings(ma, "H_HS_MISSING")] == [(2, "hard"), (5, "hard")]
    assert {f.invoice_no for f in findings(pt, "H_HDR_MISSING") if f.field == "total_pkg"} == {
        "50667175", "50667364", "50667153", "50667783", "50667440",
    }


def test_frozen_prefix():
    entries = read_extracts(FIXTURES)
    by_invoice = {d["header"]["invoice_no"]: d for d in entries}
    check_prefix(by_invoice["2000263342"], [d for inv, d in by_invoice.items() if inv.startswith("506")])
    assert not findings(by_invoice["2120411708"], "H_HS_MISSING")


def test_local_prefix():
    path = ROOT / "out/prefix_repro"
    ma_path = path / "ma_hs/0011263371_2000263342_RBTW_20260115.json"
    pt_path = path / "pt_round3"
    if not ma_path.is_file() or not pt_path.is_dir():
        pytest.skip("Original pre-fix artifacts unavailable")
    check_prefix(read_extracts(ma_path)[0], read_extracts(pt_path))
    workbook = ma_path.with_suffix(".xlsx")
    if workbook.is_file():
        report = validate(workbook, ma_path)
        assert [f.row for f in report.findings if f.rule_id == "H_HS_MISSING"] == ["Lines!3", "Lines!6"]


def test_local_pt4_prefix():
    path = Path("/workspace/pt4audit/snap_672f427.json")
    if not path.is_file():
        pytest.skip("PT 4th pre-fix snapshot unavailable")
    assert len([f for f in findings(path, "H_HDR_MISSING")
                if f.status == "hard" and f.field == "total_pkg"]) == 13


def test_display_precision_and_usage(invoice, tmp_path):
    invoice["items"][0]["unit_price"] = 10.250002
    path = tmp_path / "Result.xlsx"
    write_xlsx_many([invoice], path)
    wb = load_workbook(path)
    wb["Lines"]["D2"].number_format = "0.00"
    wb.save(path)
    assert any(f.rule_id == "H_XLSX_TYPE" and f.row == "Lines!D2"
               for f in validate(path, invoice).findings)
    with pytest.raises(SystemExit) as exc:
        main([])
    assert exc.value.code == 2


def test_pair_json_directory_uses_workbook_source_order(invoice, tmp_path):
    from invoice_extractor.export import write_json

    invoice["meta"]["source_file"] = "z.pdf"
    other = deepcopy(invoice)
    other["header"]["invoice_no"] = "OTHER"
    other["meta"]["source_file"] = "a.pdf"
    workbook = tmp_path / "Result.xlsx"
    write_xlsx_many([invoice, other], workbook)
    write_json(invoice, tmp_path / "z.json")
    write_json(other, tmp_path / "a.json")
    assert not validate(workbook, tmp_path).findings
    assert any(f.rule_id == "H_XLSX_DIFF" for f in validate(workbook, [other, invoice]).findings)


@pytest.fixture
def twins(invoice):
    invoice["meta"]["source_file"] = "batch/case/A.PDF"
    excel = deepcopy(invoice)
    excel["meta"]["source_file"] = "batch/case/B.xlsx"
    return invoice, excel


@pytest.mark.parametrize("path, count, rule", [
    ("batch/case/B.xls", 2, "W_TWIN"),
    ("batch/case/B.xlsx", 2, "W_TWIN"),
    ("batch/case/B.pdf", 2, "H_DUPLICATE"),
    ("batch/other/B.xlsx", 2, "H_DUPLICATE"),
    ("batch/case/B.xlsx", 3, "H_DUPLICATE"),
])
def test_twin_identification(twins, path, count, rule):
    pdf, excel = twins
    excel["meta"]["source_file"] = path
    rows = [pdf, excel] if count == 2 else [pdf, excel, deepcopy(pdf)]
    report = validate(extracts=rows)
    assert [f.rule_id for f in report.findings] == [rule] * count
    assert report.counts["hard"] == (count if rule == "H_DUPLICATE" else 0)


def test_twin_packing_blank_and_conflict(twins, tmp_path):
    pdf, excel = twins
    excel["header"].update(total_pkg=None, gross_weight_kg=None)
    result = tmp_path / "Result.xlsx"
    write_xlsx_many([pdf, excel], result)
    for report in (validate(result), validate(result, [pdf, excel])):
        warnings = [f for f in report.findings if f.rule_id == "W_TWIN_PKG_BLANK"]
        assert {f.field for f in warnings} == {"total_pkg", "gross_weight_kg"}
        assert all(f.row == "Summary!3" and "Summary!2" in f.note for f in warnings)
        assert report.counts["hard"] == 0

    excel["header"].update(total_pkg=3, gross_weight_kg=26)
    conflicts = findings(twins, "H_TWIN_PKG_CONFLICT")
    assert {(f.field, f.status) for f in conflicts} == {
        ("total_pkg", "hard"), ("gross_weight_kg", "hard"),
    }

    for row in twins:
        row["header"].update(total_pkg=None, gross_weight_kg=None)
    assert len(findings(twins, "H_HDR_MISSING")) == 4
    assert not findings(twins, "W_TWIN_PKG_BLANK")


def test_bl_totals_count_twins_once(twins):
    pdf, excel = twins
    other = deepcopy(pdf)
    other["header"]["invoice_no"] = "OTHER"
    for row in (*twins, other):
        row["header"].update(bl_no="BL-1", bl_packages=4, bl_gross_weight_kg=50)
    assert validate(extracts=[*twins, other]).counts["hard"] == 0

    excel["header"].update(total_pkg=None, gross_weight_kg=None)
    pdf["header"]["bl_gross_weight_kg"] = 51
    excel["header"]["bl_gross_weight_kg"] = 51
    other["header"]["bl_gross_weight_kg"] = 51
    assert [f.field for f in findings([*twins, other], "H_BL_TOTAL")] == ["bl_gross_weight_kg"]

    # Only the blank twin has an embedded BL. The carrying twin still contributes.
    for field in ("bl_no", "bl_packages", "bl_gross_weight_kg"):
        pdf["header"].pop(field)
    assert [f.field for f in findings([*twins, other], "H_BL_TOTAL")] == ["bl_gross_weight_kg"]


@pytest.mark.parametrize("profile, note, bl_no, bl_gw, rule", [
    ("saginomiya", "Use BL G.W.", None, None, "W_GW_FROM_BL"),
    ("saginomiya", "Use BL G.W.", "BL-1", 25, "W_GW_FROM_BL"),
    ("saginomiya", "Use BL G.W.", "BL-1", None, "H_HDR_MISSING"),
    ("saginomiya", "Use BL G.W.", "BL-1", 0, "H_HDR_MISSING"),
    ("saginomiya", None, "BL-1", 25, "H_HDR_MISSING"),
    ("saginomiya", "Unrelated note", "BL-1", 25, "H_HDR_MISSING"),
    ("hipus", "Use BL G.W.", "BL-1", 25, "H_HDR_MISSING"),
])
def test_saginomiya_gw_from_bl(invoice, profile, note, bl_no, bl_gw, rule):
    invoice["meta"].update(format_id="bhc_vendor_ci_v1", notes=f"profile={profile}")
    invoice["header"].update(gross_weight_kg=None, summary_note=note, bl_no=bl_no,
                             bl_gross_weight_kg=bl_gw)
    assert [(f.rule_id, f.field, f.status) for f in validate(extracts=invoice).findings] == [
        (rule, "gross_weight_kg", "warn" if rule == "W_GW_FROM_BL" else "hard"),
    ]


def test_saginomiya_separate_bill(invoice):
    invoice["meta"].update(format_id="bhc_vendor_ci_v1", notes="profile=saginomiya")
    invoice["header"].update(gross_weight_kg=None, summary_note="Use BL G.W.")
    bill = {"header": {"hbl_no": "BL-1", "invoice_refs": ["00012345"], "gross_weight_kg": 25}}
    assert [f.rule_id for f in validate(extracts=invoice, bl_extracts=bill).findings] == ["W_GW_FROM_BL"]
    bill["header"].pop("gross_weight_kg")
    assert [f.rule_id for f in validate(extracts=invoice, bl_extracts=bill).findings] == ["H_HDR_MISSING"]


@pytest.mark.parametrize("note, rule", [
    ("profile=sanhua; CUSTOMERS NO. (Bosch PN) blank on this document for P10062198-30", "W_PN_BLANK_PRINTED"),
    ("profile=sanhua; PL: 197 CTNS", "H_LINE_MISSING"),
    (None, "H_LINE_MISSING"),
])
def test_part_no_blank_on_source_needs_note(invoice, note, rule):
    """Documented sanhua rule: PN not printed -> blank + note is a warn; no note stays hard."""
    invoice["meta"].update(format_id="bhc_vendor_ci_v1", notes=note)
    invoice["items"][0]["part_no"] = None
    rules = {f.rule_id for f in validate(extracts=invoice).findings if f.field == "part_no"}
    assert rule in rules
    assert rules - {rule} == set()


# --- Auditor 2026-11-20 line tolerance --------------------------------------
# tol = |qty / pricing_unit| * (printed price unit / 2) + (printed amount unit / 2)

def _ak_line(amount, printed_amount):
    return {
        "header": {
            "invoice_no": "AK00074096", "invoice_date": "2026-10-30", "currency": "TWD",
            "amount": amount, "total_pkg": 1, "gross_weight_kg": 10, "item_line_count": 1,
        },
        "items": [{
            "part_no": "1986.AD4.020-879", "qty": 5, "unit_price": 693, "amount": amount,
            "hs_code": "84159000", "item_no": 110,
        }],
        "meta": {
            "format_id": "ma_ak_billing_v1",
            "printed_layout_text": f"110    1986.AD4.020-879     5 PC     693     {printed_amount}     0%     0",
        },
    }


def _line_math(extract):
    return [f for f in validate(extracts=extract).findings if f.rule_id in ("H_LINE_MATH", "W_ROUNDING")]


def test_line_tolerance_ak_printed_extension_is_ok():
    # 5 x 693 = 3,465 vs printed 3,464: diff 1 <= 5*0.5 + 0.5 = 3.0 -> ok, not even warn.
    assert _line_math(_ak_line(3464, "3,464")) == []


def test_line_tolerance_ak_boundary_diff_3_is_ok():
    # diff exactly 3 == tol 3.0 -> ok (hard only when diff > tol).
    assert _line_math(_ak_line(3462, "3,462")) == []


def test_line_tolerance_ak_diff_4_is_hard():
    found = _line_math(_ak_line(3461, "3,461"))
    assert [(f.status, f.rule_id) for f in found] == [("hard", "H_LINE_MATH")]
    assert "tolerance 3.0" in found[0].note


def test_line_tolerance_real_ak_layout_fixture():
    extract = _ak_line(3464, "")
    del extract["meta"]["printed_layout_text"]
    extract["meta"]["printed_layout_text_file"] = str(ROOT / "fixtures/ma_ak_AK00074096_layout.txt")
    assert _line_math(extract) == []


def test_line_tolerance_falls_back_to_cents_without_printed_text():
    # No printed text: units fall back to 0.01 -> tol 5*0.005 + 0.005 = 0.03 -> diff 1 is hard.
    extract = _ak_line(3464, "")
    del extract["meta"]["printed_layout_text"]
    assert [f.status for f in _line_math(extract)] == ["hard"]


def test_line_tolerance_respects_pricing_unit():
    # 1000 PC at 12.50 per 100 -> 125.00; tol = (1000/100)*0.005 + 0.005 = 0.055.
    def line(amount, printed):
        return {
            "header": {"invoice_no": "E1", "invoice_date": "2026-10-01", "currency": "EUR", "amount": amount,
                       "total_pkg": 1, "gross_weight_kg": 2, "item_line_count": 1},
            "items": [{"part_no": "P1", "qty": 1000, "unit_price": 12.5, "amount": amount, "pricing_unit": 100,
                       "hs_code": "84159000", "item_no": 1}],
            "meta": {"format_id": "pt_gloria_v1", "printed_layout_text": f"P1 1000 12.50 {printed}"},
        }
    assert _line_math(line(125.05, "125.05")) == []
    assert [f.status for f in _line_math(line(125.06, "125.06"))] == ["hard"]


def test_printed_total_tolerance_not_loosened_for_whole_currency():
    # Line tolerance must not leak into sum(lines) vs printed total: still 0.01.
    extract = _ak_line(3464, "3,464")
    extract["meta"]["labeled_amount"] = 3464.5
    found = [f for f in validate(extracts=extract).findings if f.rule_id == "H_PRINTED_AMOUNT"]
    assert [f.status for f in found] == ["hard"]


def test_line_tolerance_two_decimal_boundary_uses_decimal():
    # 3 x 1.11 = 3.33; tol = 3*0.005 + 0.005 = 0.02. Float math gives 3.35-3.33 = 0.0200000000000001
    # which would wrongly exceed tol; Decimal keeps diff == tol -> ok. 3.36 (diff 0.03) -> hard.
    def line(amount, printed):
        return {
            "header": {"invoice_no": "D1", "invoice_date": "2026-10-01", "currency": "EUR", "amount": amount,
                       "total_pkg": 1, "gross_weight_kg": 2, "item_line_count": 1},
            "items": [{"part_no": "P1", "qty": 3, "unit_price": 1.11, "amount": amount,
                       "hs_code": "84159000", "item_no": 1}],
            "meta": {"format_id": "pt_gloria_v1", "printed_layout_text": f"1 P1 3 1.11 {printed}"},
        }
    assert _line_math(line(3.35, "3.35")) == []
    assert [f.status for f in _line_math(line(3.36, "3.36"))] == ["hard"]
