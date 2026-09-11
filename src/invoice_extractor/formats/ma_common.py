"""Shared helpers for MA WithPeriod / NoPeriod invoice formats."""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float

# Line-item HS appears after Weight / Dispatch element / EAN rows; GEH Brake Fluid
# can push HS to offset 8+; page breaks can push HS past ~30. Scan until next pos line.
_HS = re.compile(r"HS\s*CODE\s+(\d{6,12})", re.I)

# Packing / Marking: "RB 200317606 … Gross 541.000 KG" (Gross usually same line).
_RB = re.compile(r"\bRB\s+(\d{6,})\b", re.I)
_GROSS_KG = re.compile(r"Gross\s+([\d,.]+)\s*KG", re.I)

# Next line-item starts (dotted PN or 13-char undotted).
_NEXT_ITEM = re.compile(
    r"^\s*(?:\d{5}\s+[A-Z0-9](?:\.[A-Z0-9]+){3,}|\d{5,6}\s+[A-Z0-9]{13}\b)"
)


def find_hs_after_item(lines: list[str], item_idx: int, *, max_ahead: int = 55) -> str | None:
    """Return first HS CODE after a line-item row, before the next item."""
    end = min(item_idx + 1 + max_ahead, len(lines))
    for j in range(item_idx + 1, end):
        if _NEXT_ITEM.match(lines[j]):
            break
        hm = _HS.search(lines[j])
        if hm:
            return hm.group(1)
    return None


def parse_rb_packages(text: str) -> tuple[float | None, float | None]:
    """Packages + gross weight from unique RB packing markers within one PDF.

    - ``total_pkg`` = count of unique RB numbers
    - ``gross_weight_kg`` = sum of Gross KG for those RBs (first Gross wins;
      same RB + same weight later is ignored). Different Gross for the same RB
      keeps the first value (one piece per RB id).
    """
    lines = text.splitlines()
    rb_gw: dict[str, float] = {}
    for i, line in enumerate(lines):
        rm = _RB.search(line)
        if not rm:
            continue
        chunk = "\n".join(lines[i : i + 3])
        gm = _GROSS_KG.search(chunk)
        if not gm:
            continue
        rb = rm.group(1)
        gw = us_float(gm.group(1))
        if rb in rb_gw:
            # same RB again: count once (whether weight matches or not)
            continue
        rb_gw[rb] = gw
    if not rb_gw:
        return None, None
    return float(len(rb_gw)), round(sum(rb_gw.values()), 3)
