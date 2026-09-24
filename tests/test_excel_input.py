"""Excel input acceptance, cell→text, and skip rules."""

from __future__ import annotations

from pathlib import Path

import pytest
from openpyxl import Workbook

from invoice_extractor.cli import collect_pdfs
from invoice_extractor.excel_text import (
    ExcelUnsupportedError,
    should_skip_input,
    workbook_to_text,
)
from invoice_extractor.mapping_status import LABEL_NEW_NEEDS_RULES, mapping_status
from invoice_extractor.rules_engine import extract_invoice


def _write_sample_xlsx(path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "INV"
    ws.append(["Invoice No", "Amount", "Currency"])
    ws.append(["XLSX-DEMO-001", 1234.5, "USD"])
    ws2 = wb.create_sheet("Lines")
    ws2.append(["PN", "Qty"])
    ws2.append(["ABC-1", 2])
    wb.save(path)
    wb.close()
    return path


def test_workbook_to_text_sheets_and_tabs(tmp_path: Path):
    xlsx = _write_sample_xlsx(tmp_path / "sample_inv.xlsx")
    text, backend = workbook_to_text(xlsx)
    assert backend == "excel/openpyxl"
    assert "=== Sheet: INV ===" in text
    assert "=== Sheet: Lines ===" in text
    assert "Invoice No\tAmount\tCurrency" in text
    assert "XLSX-DEMO-001\t1234.5\tUSD" in text
    assert "ABC-1\t2" in text


def test_xls_raises_clear_message(tmp_path: Path):
    fake = tmp_path / "legacy.xls"
    fake.write_bytes(b"not-a-real-xls")
    with pytest.raises(ExcelUnsupportedError, match="save as .xlsx"):
        workbook_to_text(fake)


def test_collect_accepts_xlsx_and_skips_result(tmp_path: Path):
    good = _write_sample_xlsx(tmp_path / "vendor_inv.xlsx")
    result = tmp_path / "InvoiceExtract_Result.xlsx"
    _write_sample_xlsx(result)
    template = tmp_path / "InvoiceExtract_Template.xlsx"
    _write_sample_xlsx(template)
    ocr_dir = tmp_path / "ocr_out"
    ocr_dir.mkdir()
    ocr_xlsx = ocr_dir / "scan.xlsx"
    _write_sample_xlsx(ocr_xlsx)
    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    files, errors = collect_pdfs([tmp_path])
    names = {f.name for f in files}
    assert "vendor_inv.xlsx" in names
    assert "a.pdf" in names
    assert "InvoiceExtract_Result.xlsx" not in names
    assert "InvoiceExtract_Template.xlsx" not in names
    assert "scan.xlsx" not in names  # under ocr_out/
    assert should_skip_input(result)
    assert should_skip_input(ocr_xlsx)


def test_collect_single_xlsx(tmp_path: Path):
    xlsx = _write_sample_xlsx(tmp_path / "one.xlsx")
    files, errors = collect_pdfs([xlsx])
    assert errors == []
    assert files == [xlsx]


def test_unmatched_excel_needs_rules(tmp_path: Path):
    xlsx = _write_sample_xlsx(tmp_path / "unknown_vendor.xlsx")
    result = extract_invoice(xlsx)
    data = result.to_dict()
    meta = data["meta"]
    assert meta.get("source_kind") == "excel"
    assert meta.get("text_backend") == "excel/openpyxl"
    assert meta.get("format_id") in (None, "")
    assert meta.get("needs_gold") is True
    assert mapping_status(meta, None) == LABEL_NEW_NEEDS_RULES


def test_xls_extract_notes_save_as_xlsx(tmp_path: Path):
    fake = tmp_path / "legacy.xls"
    fake.write_bytes(b"not-a-real-xls")
    result = extract_invoice(fake)
    meta = result.to_dict()["meta"]
    assert meta.get("source_kind") == "excel"
    assert meta.get("needs_gold") is True
    assert "save as .xlsx" in (meta.get("notes") or "").lower()
