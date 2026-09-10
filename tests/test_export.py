"""Excel / JSON export + CLI default extension (PDFextract-style columns)."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from openpyxl import load_workbook

from invoice_extractor.cli import _out_path_for, build_parser, collect_pdfs
from invoice_extractor.export import (
    DEFAULT_RESULT_NAME,
    LINES_COLS,
    LINES_SHEET,
    META_COLS,
    META_SHEET,
    SUMMARY_COLS,
    SUMMARY_SHEET,
    bundled_template_path,
    default_out_path,
    default_result_path,
    write_extract,
    write_xlsx,
    write_xlsx_many,
)


SAMPLE = {
    "header": {
        "invoice_no": "INV-1",
        "invoice_date": "2026-01-02",
        "vendor": "Acme",
        "amount": 12.5,
        "currency": "USD",
        "total_quantity": 3.0,
        "item_line_count": 2,
        "total_pkg": 1.0,
        "gross_weight_kg": 2.5,
        "incoterm": "FOB",
        "origin": None,
        "hs_code": None,
    },
    "items": [
        {
            "invoice_no": "INV-1",
            "part_no": "A1",
            "description": "Widget",
            "qty": 2.0,
            "unit": "pcs",
            "unit_price": 5.0,
            "amount": 10.0,
            "currency": "USD",
            "origin": "CN",
            "hs_code": "1234",
        },
        {
            "invoice_no": "INV-1",
            "part_no": "B2",
            "description": "Gadget",
            "qty": 1.0,
            "unit": "pcs",
            "unit_price": 2.5,
            "amount": 2.5,
            "currency": "USD",
            "origin": "TW",
            "hs_code": "5678",
        },
    ],
    "meta": {
        "source_file": "inv.pdf",
        "format_id": "demo_v1",
        "text_backend": "fixture",
        "confidence": "high",
        "checker_verdict": "pass",
        "needs_gold": False,
        "needs_ocr": False,
        "notes": None,
        "checker_issues": [],
    },
}


SAMPLE2 = {
    "header": {
        "invoice_no": "INV-2",
        "amount": 99.0,
        "currency": "EUR",
        "total_quantity": 5.0,
        "item_line_count": 1,
        "total_pkg": 2.0,
        "gross_weight_kg": 10.0,
        "incoterm": "CIF",
    },
    "items": [
        {
            "invoice_no": "INV-2",
            "part_no": "Z9",
            "description": "Bolt",
            "qty": 5.0,
            "unit": "pcs",
            "unit_price": 19.8,
            "amount": 99.0,
            "currency": "EUR",
            "origin": "DE",
            "hs_code": "9999",
        },
    ],
    "meta": {
        "source_file": "inv2.pdf",
        "format_id": "demo_v2",
        "text_backend": "fixture",
        "confidence": "high",
        "checker_verdict": "pass",
        "needs_gold": False,
        "needs_ocr": False,
    },
}


def test_default_out_path_xlsx():
    assert default_out_path(Path("folder/inv.pdf")) == Path("folder/inv.extract.xlsx")
    assert _out_path_for(Path("a/b.pdf"), None) == Path("a/b.extract.xlsx")
    assert _out_path_for(Path("a/b.pdf"), "out.json") == Path("out.json")
    assert _out_path_for(Path("a/b.pdf"), "out.xlsx") == Path("out.xlsx")
    assert _out_path_for(Path("a/b.pdf"), None, multi=True).name == DEFAULT_RESULT_NAME
    assert default_result_path(Path("/tmp")).name == DEFAULT_RESULT_NAME


def test_cli_help_mentions_xlsx():
    help_txt = build_parser().format_help()
    assert ".extract.xlsx" in help_txt or "xlsx" in help_txt.lower()
    assert "directories" in help_txt.lower() or "PDF" in help_txt


def test_bundled_template_exists():
    tpl = bundled_template_path()
    assert tpl is not None
    assert tpl.is_file()
    assert tpl.name == "InvoiceExtract_Template.xlsx"
    wb = load_workbook(tpl)
    assert SUMMARY_SHEET in wb.sheetnames
    assert LINES_SHEET in wb.sheetnames
    assert META_SHEET in wb.sheetnames
    assert [c.value for c in wb[SUMMARY_SHEET][1]] == list(SUMMARY_COLS)
    assert [c.value for c in wb[LINES_SHEET][1]] == list(LINES_COLS)


def test_write_xlsx_pdfextract_columns(tmp_path: Path):
    path = tmp_path / "out.xlsx"
    write_xlsx(SAMPLE, path)
    assert path.is_file()
    wb = load_workbook(path)
    assert SUMMARY_SHEET in wb.sheetnames
    assert LINES_SHEET in wb.sheetnames
    assert META_SHEET in wb.sheetnames

    ws_h = wb[SUMMARY_SHEET]
    headers = [c.value for c in ws_h[1]]
    assert headers == list(SUMMARY_COLS)
    assert "Invoice No." in headers
    assert "Invoice Value" in headers
    assert "Invoice Currency" in headers
    row = {headers[i]: ws_h[2][i].value for i in range(len(headers))}
    assert row["Invoice No."] == "INV-1"
    assert row["Invoice Value"] == 12.5
    assert row["Invoice Currency"] == "USD"
    assert row["Packages"] == 1.0
    assert row["LINE"] == 2
    assert row["QTY"] == 3.0

    ws_i = wb[LINES_SHEET]
    item_headers = [c.value for c in ws_i[1]]
    assert item_headers == list(LINES_COLS)
    assert "PN" in item_headers
    assert "InvoiceNumber" in item_headers
    assert ws_i.max_row == 3  # header + 2 items
    pn_idx = item_headers.index("PN")
    assert ws_i[2][pn_idx].value == "A1"
    assert ws_i[3][pn_idx].value == "B2"
    des_idx = item_headers.index("Des")
    assert ws_i[2][des_idx].value == "Widget"
    unt_idx = item_headers.index("Unt")
    assert ws_i[2][unt_idx].value == 5.0  # unit_price
    uom_idx = item_headers.index("UoM")
    assert ws_i[2][uom_idx].value == "pcs"

    ws_m = wb[META_SHEET]
    meta_headers = [c.value for c in ws_m[1]]
    assert meta_headers[0] == "source_file"
    assert "status" in meta_headers
    status_idx = meta_headers.index("status")
    src_idx = meta_headers.index("source_file")
    assert ws_m[2][src_idx].value == "inv.pdf"
    assert ws_m[2][status_idx].value == "ok"
    fmt_idx = meta_headers.index("format_id")
    assert ws_m[2][fmt_idx].value == "demo_v1"


def test_write_xlsx_many_appends_two_invoices(tmp_path: Path):
    path = tmp_path / "batch.xlsx"
    write_xlsx_many([SAMPLE, SAMPLE2], path)
    wb = load_workbook(path)
    ws_s = wb[SUMMARY_SHEET]
    assert ws_s.max_row == 3  # header + 2 invoices
    headers = [c.value for c in ws_s[1]]
    inv_idx = headers.index("Invoice No.")
    val_idx = headers.index("Invoice Value")
    assert ws_s[2][inv_idx].value == "INV-1"
    assert ws_s[2][val_idx].value == 12.5
    assert ws_s[3][inv_idx].value == "INV-2"
    assert ws_s[3][val_idx].value == 99.0  # own totals, not grand sum

    ws_l = wb[LINES_SHEET]
    assert ws_l.max_row == 1 + 2 + 1  # header + 2 + 1 lines
    line_h = [c.value for c in ws_l[1]]
    invn = line_h.index("InvoiceNumber")
    assert ws_l[2][invn].value == "INV-1"
    assert ws_l[4][invn].value == "INV-2"

    ws_m = wb[META_SHEET]
    assert ws_m.max_row == 3
    assert ws_m[2][0].value == "inv.pdf"
    assert ws_m[3][0].value == "inv2.pdf"


def test_template_clear_and_rewrite(tmp_path: Path):
    """Second write must clear prior data rows, not append forever."""
    tpl = bundled_template_path()
    assert tpl is not None
    path = tmp_path / "reuse.xlsx"
    write_xlsx_many([SAMPLE, SAMPLE2], path, template=tpl)
    wb1 = load_workbook(path)
    assert wb1[SUMMARY_SHEET].max_row == 3
    assert wb1[LINES_SHEET].max_row == 4

    # Rewrite with only SAMPLE — old INV-2 rows must disappear
    write_xlsx_many([SAMPLE], path, template=path)  # use previous as template-like
    # Actually use bundled template again to simulate each run from template
    write_xlsx_many([SAMPLE], path, template=tpl)
    wb2 = load_workbook(path)
    assert wb2[SUMMARY_SHEET].max_row == 2
    headers = [c.value for c in wb2[SUMMARY_SHEET][1]]
    assert headers == list(SUMMARY_COLS)
    assert wb2[SUMMARY_SHEET][2][0].value == "INV-1"
    assert wb2[LINES_SHEET].max_row == 3
    assert wb2[META_SHEET].max_row == 2
    # Header formatting from template preserved (bold / fill)
    cell = wb2[SUMMARY_SHEET].cell(1, 1)
    assert cell.value == "Invoice No."
    assert cell.font.bold is True


def test_write_xlsx_many_with_failures_in_meta(tmp_path: Path):
    path = tmp_path / "partial.xlsx"
    write_xlsx_many(
        [SAMPLE],
        path,
        failures=[{"source_file": "bad.pdf", "error": "boom", "meta": {"source_file": "bad.pdf"}}],
    )
    wb = load_workbook(path)
    assert wb[SUMMARY_SHEET].max_row == 2  # only success
    ws_m = wb[META_SHEET]
    assert ws_m.max_row == 3  # ok + error
    meta_h = [c.value for c in ws_m[1]]
    status_i = meta_h.index("status")
    err_i = meta_h.index("error")
    assert ws_m[2][status_i].value == "ok"
    assert ws_m[3][status_i].value == "error"
    assert ws_m[3][err_i].value == "boom"


def test_write_extract_routes_by_extension(tmp_path: Path):
    xlsx = write_extract(SAMPLE, tmp_path / "a.xlsx")
    assert xlsx.suffix == ".xlsx"
    assert xlsx.is_file()
    wb = load_workbook(xlsx)
    assert SUMMARY_SHEET in wb.sheetnames

    jpath = write_extract(SAMPLE, tmp_path / "b.json")
    assert jpath.suffix == ".json"
    data = json.loads(jpath.read_text(encoding="utf-8"))
    assert data["header"]["invoice_no"] == "INV-1"
    # JSON keeps internal schema
    assert "invoice_no" in data["header"]
    assert "part_no" in data["items"][0]

    xls = write_extract(SAMPLE, tmp_path / "c.xls")
    assert xls.suffix == ".xlsx"
    assert xls.is_file()


def test_collect_pdfs_dir_and_files(tmp_path: Path):
    d = tmp_path / "inbox"
    d.mkdir()
    (d / "a.pdf").write_bytes(b"%PDF")
    (d / "b.PDF").write_bytes(b"%PDF")
    (d / "note.txt").write_text("x")
    single = tmp_path / "c.pdf"
    single.write_bytes(b"%PDF")
    pdfs, errs = collect_pdfs([str(d), str(single)])
    names = sorted(p.name.lower() for p in pdfs)
    assert names == ["a.pdf", "b.pdf", "c.pdf"]
    assert errs == []
