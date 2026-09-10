"""Write extract results to Excel (.xlsx) or JSON.

Default Excel layout mirrors PDFextract.xlsm-style columns (Summary + Lines),
not the internal snake_case engineering schema. JSON keeps the full internal
schema for Auditor / automation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# PDFextract-style Summary sheet (one row per invoice extract for now).
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


def default_out_path(pdf: Path) -> Path:
    """``invoice.pdf`` → ``invoice.extract.xlsx``."""
    return pdf.with_name(f"{pdf.stem}.extract.xlsx")


def is_json_out(path: Path) -> bool:
    return path.suffix.lower() == ".json"


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


def write_xlsx(data: dict[str, Any], path: Path) -> None:
    """Write workbook with sheets ``Summary``, ``Lines``, ``meta``.

    Column names match PDFextract.xlsm (PT / PT_Declaration style).
    Multiple invoice rows can be appended later; currently one extract → one
    Summary row + N Lines rows.
    """
    from openpyxl import Workbook

    wb = Workbook()
    header = dict(data.get("header") or {})
    items = list(data.get("items") or [])
    meta = dict(data.get("meta") or {})

    ws_s = wb.active
    ws_s.title = SUMMARY_SHEET
    ws_s.append(list(SUMMARY_COLS))
    ws_s.append([_cell(v) for v in _summary_row(header)])

    ws_l = wb.create_sheet(LINES_SHEET)
    ws_l.append(list(LINES_COLS))
    for it in items:
        ws_l.append([_cell(v) for v in _lines_row(it or {}, header)])

    ws_m = wb.create_sheet(META_SHEET)
    meta_keys = [k for k in _META_KEYS if k in meta] + [
        k for k in meta if k not in _META_KEYS
    ]
    ws_m.append(["key", "value"])
    for k in meta_keys:
        ws_m.append([k, _cell(meta.get(k))])

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def write_json(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def write_extract(data: dict[str, Any], path: Path) -> Path:
    """Route by extension: ``.json`` → JSON; otherwise Excel (``.xlsx``).

    Returns the path actually written (``.xls`` is normalized to ``.xlsx``).
    """
    if is_json_out(path):
        write_json(data, path)
        return path
    out = path if path.suffix.lower() == ".xlsx" else path.with_suffix(".xlsx")
    write_xlsx(data, out)
    return out
