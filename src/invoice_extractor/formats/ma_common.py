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


def parse_rb_units(text: str) -> dict[str, float]:
    """``{RB unique key: Gross KG}`` in document order (first Gross wins).

    Same key rules as :func:`parse_rb_packages`. Stored on ``meta.packing_units``
    so pairing can count an RB shared by several invoices of one shipment only
    once (:func:`invoice_extractor.pairing.dedupe_shared_packing_units`).
    """
    return _rb_units(text)


def parse_rb_packages(text: str) -> tuple[float | None, float | None]:
    """Packages + gross weight from unique RB packing markers within one PDF.

    Unique key = first digit group after ``RB``, concatenated with an optional
    second digit group when present (same line, or immediately next line alone
    — NoPeriod layout). Single-segment forms (WithPeriod) keep first only.

    - ``total_pkg`` = count of unique RB keys
    - ``gross_weight_kg`` = sum of Gross KG for those keys (first Gross wins;
      duplicate keys ignore repeat weight).
    """
    rb_gw = _rb_units(text)
    if not rb_gw:
        return None, None
    return float(len(rb_gw)), round(sum(rb_gw.values()), 3)


def _rb_units(text: str) -> dict[str, float]:
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
    return rb_gw



# AK Marking HU: only the first line of a block has the literal "RB"; later
# 15–20 digit handling-unit IDs sit on their own Dummy Pack line. Unique key
# is that HU id alone (do not concat a second digit group — dimensions and
# weights on the same line are not a NoPeriod second segment).
_AK_HU = re.compile(
    r"^\s*(?:RB\s+)?(\d{15,20})\s+Dummy Pack\. Mat\.",
    re.I,
)
# "Gross 5.000 KG" (older AK) or "Gross HU Weight 17.800 KG" (newer AK).
# Does not match "Net HU Weight" or "Gross Product Weight".
_AK_GROSS = re.compile(
    r"Gross(?:\s+HU(?:\s+Weight)?)?\s+([\d,.]+)\s*KG",
    re.I,
)
_AK_SUMMARY = re.compile(r"^\s*\d{1,4}\s+Dummy Pack\. Mat\.", re.I)
_AK_STOP = re.compile(
    r"Total Num of Packages|Tax Information:|The document is valid",
    re.I,
)


def parse_ak_units(text: str) -> dict[str, float]:
    """``{HU id: Gross HU Weight KG}`` in document order (first Gross wins).

    Stored on ``meta.packing_units`` so pairing can count an HU that repeats
    across invoices of one shipment only once
    (:func:`invoice_extractor.pairing.dedupe_shared_packing_units`).
    """
    mark = text[text.find("Marking") :] if "Marking" in text else text
    lines = mark.splitlines()
    hu_gw: dict[str, float] = {}
    i = 0
    while i < len(lines):
        hm = _AK_HU.match(lines[i])
        if not hm:
            i += 1
            continue
        hu = hm.group(1)
        gw = None
        # Same line, then following lines (page-break / footer may sit between
        # the HU id and Gross, or Gross may already be on the HU line with Net
        # on the next page). Stop at the next HU, the type-summary block, or
        # the printed totals. Skip POS-no / Net Val / footer noise.
        end = min(i + 25, len(lines))
        for j in range(i, end):
            if j > i and (_AK_HU.match(lines[j]) or _AK_SUMMARY.match(lines[j]) or _AK_STOP.search(lines[j])):
                break
            gm = _AK_GROSS.search(lines[j])
            if gm:
                gw = us_float(gm.group(1))
                break
        if gw is not None and hu not in hu_gw:
            hu_gw[hu] = gw
        i += 1
    return hu_gw


def parse_ak_packages(text: str) -> tuple[float | None, float | None]:
    """Packages + GW for MA Billing-Document (AK) invoices.

    Prefer unique handling-unit IDs under the Marking section (with or without
    a leading ``RB``). Fall back to ``Total Num of Packages`` plus summary
    ``Dummy Pack. Mat.`` Gross lines when HU markers are incomplete.
    """
    hu_gw = parse_ak_units(text)
    if hu_gw:
        return float(len(hu_gw)), round(sum(hu_gw.values()), 3)

    tot = re.search(r"Total Num of Packages\s+(\d+)", text, re.I)
    pkg = float(tot.group(1)) if tot else None
    # Summary lines: "1  Dummy Pack. Mat. for Carton  Net … Gross X KG"
    gw_vals = [
        us_float(g)
        for g in re.findall(
            r"^\s*\d+\s+Dummy Pack\. Mat\.[^\n]*?Gross\s+([\d,.]+)\s*KG",
            text,
            re.I | re.M,
        )
    ]
    if gw_vals:
        gw = round(sum(gw_vals), 3)
        if pkg is None:
            pkg = float(len(gw_vals))
        return pkg, gw
    if pkg is not None:
        return pkg, None
    return None, None
