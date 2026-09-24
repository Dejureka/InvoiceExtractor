"""Convert Excel workbooks to layout-ish text for FormatSOP matching."""

from __future__ import annotations

from pathlib import Path

EXCEL_SUFFIXES = frozenset({".xlsx", ".xlsm", ".xls"})
OPENPYXL_SUFFIXES = frozenset({".xlsx", ".xlsm"})

# Tool outputs / templates that must not be treated as invoice inputs.
SKIP_INPUT_NAMES = frozenset(
    {
        "invoiceextract_result.xlsx",
        "invoiceextract_template.xlsx",
        "blextract_result.xlsx",
    }
)


class ExcelUnsupportedError(ValueError):
    """Raised for legacy .xls or unreadable workbooks with a user-facing message."""


def is_excel_path(path: str | Path) -> bool:
    return Path(path).suffix.lower() in EXCEL_SUFFIXES


def is_openpyxl_excel(path: str | Path) -> bool:
    return Path(path).suffix.lower() in OPENPYXL_SUFFIXES


def should_skip_input(path: str | Path) -> bool:
    """True for tool Result/Template Excel or anything under ``ocr_out/``."""
    p = Path(path)
    if p.name.lower() in SKIP_INPUT_NAMES:
        return True
    # Any path segment named ocr_out (portable or nested)
    return any(part.lower() == "ocr_out" for part in p.parts)


def workbook_to_text(path: str | Path) -> tuple[str, str]:
    """Return ``(text, backend)`` from an Excel workbook.

    Sheets become blocks headed by ``=== Sheet: <name> ===``; each row is
    non-empty cells joined by a tab. Empty rows are kept as blank lines so
    block structure stays visible for future Excel FormatSOP rules.
    """
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".xls":
        return _workbook_to_text_xlrd(p)
    if suffix not in OPENPYXL_SUFFIXES:
        raise ExcelUnsupportedError(f"Not an Excel workbook: {p}")
    return _workbook_to_text_openpyxl(p)


def _cells_to_blocks(sheet_rows: list[tuple[str, list[list[object]]]]) -> str:
    """Build ``=== Sheet ===`` + tab-joined non-empty cells from row values."""
    blocks: list[str] = []
    for title, rows in sheet_rows:
        lines = [f"=== Sheet: {title} ==="]
        for row in rows:
            cells: list[str] = []
            for cell in row:
                if cell is None:
                    continue
                s = str(cell).strip()
                if s:
                    cells.append(s)
            lines.append("\t".join(cells) if cells else "")
        blocks.append("\n".join(lines).rstrip())
    return "\n\n".join(blocks).strip() + ("\n" if blocks else "")


def _workbook_to_text_openpyxl(p: Path) -> tuple[str, str]:
    try:
        from openpyxl import load_workbook
    except ImportError as exc:  # pragma: no cover
        raise ExcelUnsupportedError(
            "openpyxl is required to read .xlsx/.xlsm inputs"
        ) from exc

    try:
        wb = load_workbook(p, read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        raise ExcelUnsupportedError(f"Cannot open Excel file {p.name}: {exc}") from exc

    sheet_rows: list[tuple[str, list[list[object]]]] = []
    try:
        for sheet in wb.worksheets:
            rows = [list(row) for row in sheet.iter_rows(values_only=True)]
            sheet_rows.append((sheet.title, rows))
    finally:
        wb.close()
    return _cells_to_blocks(sheet_rows), "excel/openpyxl"


def _workbook_to_text_xlrd(p: Path) -> tuple[str, str]:
    """Legacy BIFF .xls via xlrd (pure Python)."""
    try:
        import xlrd
    except ImportError as exc:  # pragma: no cover
        raise ExcelUnsupportedError(
            f"Legacy .xls requires xlrd ({p.name}). "
            "Install xlrd or save as .xlsx and retry."
        ) from exc

    try:
        book = xlrd.open_workbook(str(p), formatting_info=False)
    except Exception as exc:  # noqa: BLE001
        raise ExcelUnsupportedError(f"Cannot open Excel file {p.name}: {exc}") from exc

    sheet_rows: list[tuple[str, list[list[object]]]] = []
    for sheet in book.sheets():
        rows: list[list[object]] = []
        for r in range(sheet.nrows):
            row_vals: list[object] = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                # xlrd: 3=date; convert to ISO-ish string when possible
                if cell.ctype == xlrd.XL_CELL_DATE:
                    try:
                        from datetime import datetime
                        t = xlrd.xldate_as_tuple(cell.value, book.datemode)
                        row_vals.append(datetime(*t).isoformat(sep=" ", timespec="seconds"))
                    except Exception:
                        row_vals.append(cell.value)
                elif cell.ctype == xlrd.XL_CELL_EMPTY:
                    row_vals.append(None)
                elif cell.ctype == xlrd.XL_CELL_NUMBER:
                    # Prefer int when whole number
                    v = cell.value
                    if isinstance(v, float) and v.is_integer():
                        row_vals.append(int(v))
                    else:
                        row_vals.append(v)
                else:
                    row_vals.append(cell.value)
            rows.append(row_vals)
        sheet_rows.append((sheet.name, rows))
    return _cells_to_blocks(sheet_rows), "excel/xlrd"
