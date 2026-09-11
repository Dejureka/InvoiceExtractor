"""Write extract results to Excel (.xlsx) or JSON.

Default Excel layout mirrors PDFextract.xlsm-style columns (Summary + Lines),
not the internal snake_case engineering schema. JSON keeps the full internal
schema for Auditor / automation.

Each Excel run loads the bundled fixed template (if present), clears previous
data rows (headers/formatting kept), and writes fresh results. Multiple
invoices append into one workbook.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# PDFextract-style Summary sheet (one row per invoice).
SUMMARY_SHEET = "Summary"
SUMMARY_COLS = [
    "Invoice No.",
    "Packages",
    "Package Mode",
    "G.W. (kgs)-Air DIM. (CBM)-Sea",
    "Incoterms",
    "Invoice Value",
    "LINE",
    "QTY",
    "Invoice Currency",
]

# PDFextract-style detail / declaration lines.
LINES_SHEET = "Lines"
LINES_COLS = [
    "PN",
    "Des",
    "Qty",
    "Unt",
    "Amt",
    "UoM",
    "Co",
    "HS code",
    "N.W.",
    "InvoiceNumber",
    "Currency",
]

META_SHEET = "meta"

_META_KEYS = [
    "source_file",
    "format_id",
    "text_backend",
    "confidence",
    "checker_verdict",
    "needs_gold",
    "needs_ocr",
    "notes",
    "labeled_amount",
    "labeled_amount_label",
    "checker_issues",
    "checker_details",
]

# Columnar meta headers (template / multi-file).
META_COLS = list(_META_KEYS) + ["status", "error"]

DEFAULT_RESULT_NAME = "InvoiceExtract_Result.xlsx"
TEMPLATE_REL = Path("data") / "templates" / "InvoiceExtract_Template.xlsx"


def tool_root() -> Path:
    """Writable outermost tool root (never PyInstaller ``_MEIPASS``).

    - Frozen: directory containing ``InvoiceExtractor.exe`` (``sys.executable`` parent).
    - Dev / ``python -m``: directory that holds ``data/templates/InvoiceExtract_Template.xlsx``
      (repo/package outer root), else project root next to ``pyproject.toml`` / ``data/``,
      else ``Path.cwd()``.
    """
    if getattr(sys, "frozen", False):
        try:
            return Path(sys.executable).resolve().parent
        except Exception:
            return Path.cwd()

    here = Path(__file__).resolve()
    candidates = [
        here.parents[2],  # repo root: src/invoice_extractor/export.py
        here.parents[1],  # package root (some installs)
        Path.cwd(),
    ]
    for base in candidates:
        if (base / TEMPLATE_REL).is_file():
            return base
    for base in candidates:
        if (base / "pyproject.toml").is_file() or (base / "data").is_dir():
            return base
    return Path.cwd()


def default_result_path(root: Path | None = None) -> Path:
    """Always ``InvoiceExtract_Result.xlsx`` at the tool outermost root.

    Same file every run (callers clear/rewrite via template). Explicit ``--out`` /
    Browse override this. Pass ``root`` only in tests to pin the base directory.
    """
    base = root if root is not None else tool_root()
    return Path(base) / DEFAULT_RESULT_NAME


def is_json_out(path: Path) -> bool:
    return path.suffix.lower() == ".json"


def bundled_template_path() -> Path | None:
    """Locate shipped ``InvoiceExtract_Template.xlsx`` (dev / installed / frozen)."""
    candidates: list[Path] = []
    # Project root when running from source: src/invoice_extractor/export.py → parents[2]
    here = Path(__file__).resolve()
    candidates.append(here.parents[2] / TEMPLATE_REL)
    # Next to package (editable / some installs)
    candidates.append(here.parents[1] / TEMPLATE_REL)
    # CWD (portable unzip layout)
    candidates.append(Path.cwd() / TEMPLATE_REL)
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.insert(0, Path(meipass) / TEMPLATE_REL)
        try:
            candidates.insert(0, Path(sys.executable).resolve().parent / TEMPLATE_REL)
        except Exception:
            pass
    for p in candidates:
        if p.is_file():
            return p
    return None


def _cell(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return v


def _summary_row(header: dict[str, Any]) -> list[Any]:
    """Map internal header → PDFextract Summary columns."""
    pkg_mode = header.get("package_mode")
    if pkg_mode is None:
        pkg_mode = header.get("Package Mode")
    return [
        header.get("invoice_no"),
        header.get("total_pkg"),
        pkg_mode,  # blank when format does not provide it
        header.get("gross_weight_kg"),
        header.get("incoterm"),
        header.get("amount"),
        header.get("item_line_count"),
        header.get("total_quantity"),
        header.get("currency"),
    ]


def _lines_row(item: dict[str, Any], header: dict[str, Any]) -> list[Any]:
    """Map internal item → PDFextract Lines columns."""
    inv = item.get("invoice_no") or header.get("invoice_no")
    cur = item.get("currency") or header.get("currency")
    nw = item.get("net_weight")
    if nw is None:
        nw = item.get("net_weight_kg")
    return [
        item.get("part_no"),
        item.get("description"),
        item.get("qty"),
        item.get("unit_price"),
        item.get("amount"),
        item.get("unit"),
        item.get("origin"),
        item.get("hs_code"),
        nw,
        inv,
        cur,
    ]


def _meta_row(meta: dict[str, Any], *, status: str = "ok", error: str | None = None) -> list[Any]:
    return [_cell(meta.get(k)) for k in _META_KEYS] + [_cell(status), _cell(error)]


def _clear_data_rows(ws) -> None:
    """Remove all rows below the header (row 1); keep formatting on row 1."""
    if ws.max_row > 1:
        ws.delete_rows(2, ws.max_row - 1)


def _ensure_sheet_headers(ws, title: str, cols: list[str]) -> None:
    """Ensure sheet exists with expected header row; create if missing."""
    ws.title = title
    if ws.max_row < 1 or all(c.value is None for c in ws[1]):
        for i, name in enumerate(cols, 1):
            ws.cell(1, i, name)
        return
    # If first cell doesn't look like our header, rewrite header row
    first = ws.cell(1, 1).value
    if first != cols[0]:
        for i, name in enumerate(cols, 1):
            ws.cell(1, i, name)


def _load_workbook_for_write(template: Path | None = None):
    """Load template (or build blank workbook with headers)."""
    from openpyxl import Workbook, load_workbook

    tpl = template if template is not None else bundled_template_path()
    if tpl is not None and Path(tpl).is_file():
        wb = load_workbook(Path(tpl))
    else:
        wb = Workbook()
        ws = wb.active
        ws.title = SUMMARY_SHEET
        ws.append(list(SUMMARY_COLS))
        wb.create_sheet(LINES_SHEET).append(list(LINES_COLS))
        wb.create_sheet(META_SHEET).append(list(META_COLS))

    # Guarantee sheet names / headers
    if SUMMARY_SHEET in wb.sheetnames:
        ws_s = wb[SUMMARY_SHEET]
    else:
        ws_s = wb.active
        ws_s.title = SUMMARY_SHEET
    _ensure_sheet_headers(ws_s, SUMMARY_SHEET, SUMMARY_COLS)

    if LINES_SHEET in wb.sheetnames:
        ws_l = wb[LINES_SHEET]
    else:
        ws_l = wb.create_sheet(LINES_SHEET)
    _ensure_sheet_headers(ws_l, LINES_SHEET, LINES_COLS)

    if META_SHEET in wb.sheetnames:
        ws_m = wb[META_SHEET]
    else:
        ws_m = wb.create_sheet(META_SHEET)
    # Accept legacy key/value meta; upgrade header to columnar when clearing
    _ensure_sheet_headers(ws_m, META_SHEET, META_COLS)

    _clear_data_rows(ws_s)
    _clear_data_rows(ws_l)
    _clear_data_rows(ws_m)
    return wb


def write_xlsx_many(
    extracts: list[dict[str, Any]],
    path: Path,
    *,
    template: Path | None = None,
    failures: list[dict[str, Any]] | None = None,
) -> Path:
    """Write one or more invoice extracts into a single workbook.

    - ``Summary``: one row per successful invoice (that invoice's own totals).
    - ``Lines``: all line items, keyed by InvoiceNumber.
    - ``meta``: one row per file (success + optional failures).

    Clears previous data rows from the template while keeping headers/format.
    """
    wb = _load_workbook_for_write(template)
    ws_s = wb[SUMMARY_SHEET]
    ws_l = wb[LINES_SHEET]
    ws_m = wb[META_SHEET]

    for data in extracts:
        header = dict(data.get("header") or {})
        items = list(data.get("items") or [])
        meta = dict(data.get("meta") or {})
        ws_s.append([_cell(v) for v in _summary_row(header)])
        for it in items:
            ws_l.append([_cell(v) for v in _lines_row(it or {}, header)])
        ws_m.append(_meta_row(meta, status="ok", error=None))

    for fail in failures or []:
        meta = dict(fail.get("meta") or {})
        if "source_file" not in meta and fail.get("source_file"):
            meta["source_file"] = fail.get("source_file")
        ws_m.append(
            _meta_row(
                meta,
                status="error",
                error=str(fail.get("error") or fail.get("message") or "failed"),
            )
        )

    path = Path(path)
    if path.suffix.lower() != ".xlsx":
        path = path.with_suffix(".xlsx")
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def write_xlsx(data: dict[str, Any], path: Path, *, template: Path | None = None) -> None:
    """Write workbook with sheets ``Summary``, ``Lines``, ``meta`` (single extract)."""
    write_xlsx_many([data], path, template=template)


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_json_many(extracts: list[dict[str, Any]], path: Path) -> Path:
    """Batch JSON: if ``path`` is ``.json``, write a directory ``<stem>_json/`` with one file each.

    Single extract still writes the given ``.json`` path directly via ``write_extract``.
    """
    path = Path(path)
    if len(extracts) == 1:
        write_json(extracts[0], path)
        return path
    out_dir = path if path.suffix == "" or path.is_dir() else path.with_suffix("").parent / (
        path.stem + "_json"
    )
    if path.suffix.lower() == ".json":
        out_dir = path.parent / (path.stem + "_json")
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, data in enumerate(extracts):
        meta = data.get("meta") or {}
        src = meta.get("source_file") or f"invoice_{i + 1}"
        stem = Path(str(src)).stem or f"invoice_{i + 1}"
        dest = out_dir / f"{stem}.json"
        # Avoid overwrite collisions
        n = 2
        while dest.exists():
            dest = out_dir / f"{stem}_{n}.json"
            n += 1
        write_json(data, dest)
    return out_dir


def write_extract(data: dict[str, Any], path: Path, *, template: Path | None = None) -> Path:
    """Route by extension: ``.json`` → JSON; otherwise Excel (``.xlsx``).

    Returns the path actually written (``.xls`` is normalized to ``.xlsx``).
    """
    if is_json_out(path):
        write_json(data, path)
        return path
    out = path if path.suffix.lower() == ".xlsx" else path.with_suffix(".xlsx")
    write_xlsx(data, out, template=template)
    return out


def write_extracts(
    extracts: list[dict[str, Any]],
    path: Path,
    *,
    template: Path | None = None,
    failures: list[dict[str, Any]] | None = None,
) -> Path:
    """Write one or many extracts. Excel is primary; JSON batch → folder of files."""
    path = Path(path)
    if is_json_out(path):
        return write_json_many(extracts, path)
    out = path if path.suffix.lower() == ".xlsx" else path.with_suffix(".xlsx")
    return write_xlsx_many(extracts, out, template=template, failures=failures)
