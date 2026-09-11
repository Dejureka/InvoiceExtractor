"""Shared helpers for MA WithPeriod / NoPeriod invoice formats."""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float

# Line-item HS appears after Weight / Dispatch element / EAN rows; GEH Brake Fluid
# can push HS to offset 8+; page breaks can push HS past ~30. Scan until next pos line.
_HS = re.compile(r"HS\s*CODE\s+(\d{6,12})", re.I)

# Packing / Marking:
#   WP: "RB 200317606 … Gross 541.000 KG" (single segment)
#   NP: "RB 40670214025622 … Gross …" then next line "6531" (two-segment unique key)
_RB = re.compile(r"\bRB\s+(\d{6,})(?:\s+(\d{3,8}))?\b", re.I)
_RB_SECOND_LINE = re.compile(r"^\s*(\d{3,8})\s*$")
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

    Unique key = first digit group after ``RB``, concatenated with an optional
    second digit group when present (same line, or immediately next line alone
    — NoPeriod layout). Single-segment forms (WithPeriod) keep first only.

    - ``total_pkg`` = count of unique RB keys
    - ``gross_weight_kg`` = sum of Gross KG for those keys (first Gross wins;
      duplicate keys ignore repeat weight).
    """
    lines = text.splitlines()
    rb_gw: dict[str, float] = {}
    for i, line in enumerate(lines):
        rm = _RB.search(line)
        if not rm:
            continue
        first = rm.group(1)
        second = rm.group(2)
        if not second and i + 1 < len(lines):
            sm = _RB_SECOND_LINE.match(lines[i + 1])
            if sm:
                second = sm.group(1)
        rb = first + second if second else first
        chunk = "\n".join(lines[i : i + 3])
        gm = _GROSS_KG.search(chunk)
        if not gm:
            continue
        gw = us_float(gm.group(1))
        if rb in rb_gw:
            # same unique key again: count once (whether weight matches or not)
            continue
        rb_gw[rb] = gw
    if not rb_gw:
        return None, None
    return float(len(rb_gw)), round(sum(rb_gw.values()), 3)
