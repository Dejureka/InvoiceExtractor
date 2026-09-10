"""Write extract results to Excel (.xlsx) or JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Preferred column order for header sheet (extras appended after).
_HEADER_COLS = [
    "invoice_no",
    "invoice_date",
    "vendor",
    "amount",
    "currency",
    "total_quantity",
    "item_line_count",
    "total_pkg",
    "gross_weight_kg",
    "incoterm",
    "origin",
    "hs_code",
]

_ITEM_COLS = [
    "invoice_no",
    "part_no",
    "description",
    "qty",
    "unit",
    "unit_price",
    "amount",
    "currency",
    "origin",
    "hs_code",
]

_META_KEYS = [
    "source_file",
    "format_id",
    "text_backend",
    "confidence",
    "checker_verdict",
    "needs_gold",
    "needs_ocr",
    "notes",
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


def write_xlsx(data: dict[str, Any], path: Path) -> None:
    """Write workbook with sheets ``header``, ``items``, ``meta``."""
    from openpyxl import Workbook

    wb = Workbook()

    # --- header: one-row table ---
    ws_h = wb.active
    ws_h.title = "header"
    header = dict(data.get("header") or {})
    cols = list(_HEADER_COLS) + [k for k in header if k not in _HEADER_COLS]
    ws_h.append(cols)
    ws_h.append([_cell(header.get(c)) for c in cols])

    # --- items ---
    ws_i = wb.create_sheet("items")
    items = list(data.get("items") or [])
    extra: list[str] = []
    seen = set(_ITEM_COLS)
    for it in items:
        for k in it or {}:
            if k not in seen:
                extra.append(k)
                seen.add(k)
    item_keys = list(_ITEM_COLS) + extra
    ws_i.append(item_keys)
    for it in items:
        row = it or {}
        ws_i.append([_cell(row.get(c)) for c in item_keys])

    # --- meta ---
    ws_m = wb.create_sheet("meta")
    meta = dict(data.get("meta") or {})
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
