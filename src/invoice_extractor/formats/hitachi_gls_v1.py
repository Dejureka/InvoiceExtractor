"""Hitachi Global Life Solutions (MEH) shipping advice / invoice v1.

Trained on SD(TW)_20260126_MEH6A036 layout text (detail sheet: ``Item#
Description Material`` + ``PN:`` line).

BHC 4th case6 (``20260923_MEH6J044(…).pdf``): accessory invoice — items are
inline on the invoice page (``ITEM#`` then ``01  PC-ALHZ1  1,000 PCS  4,302
4,302,000`` + ``ACCESSORY: …`` on the next line, no ``PN:``); PN = Hitachi
model; per-model origin from ``PC-AWR,PC-ARFG2-T -ORIGIN: CHINA`` /
``OTHERS -ORIGIN: JAPAN``. Packing TOTAL row uses thousands commas
(``TOTAL : 16  4,815  1,646.0  1,998  25.300``).

BHC MEH6L040 (same inline layout): model ``P-AP90DNA*EX`` (hyphen 2nd char,
``*`` variant suffix) in rows and in the ORIGIN list; descriptions share text
lines with the Marks & Numbers column (read from the item column); packing
TOTAL row has PALLETS only, CARTONS + ``N PACKAGES`` printed below it.
"""

from __future__ import annotations

import re

from invoice_extractor import windows
from invoice_extractor.fallback import fallback
from invoice_extractor.schema import (
    ExtractResult,
    Header,
    Item,
    Meta,
    en_date_to_iso,
    us_float,
)

MATCH_HINTS = {
    "filename_regex": r"MEH|HITACHI|GLS|SD\(TW\)",
    "keywords": [
        "GLOBAL LIFE SOLUTIONS",
        "HITACHI",
        "SHIPPING ADVICE",
        "JAPANESE YEN",
        "MEH",
    ],
}

NOTES = (
    "Hitachi GLS shipping advice + invoice detail; seed from MEH6A036. "
    "BHC 4th MEH6J044: inline accessory layout (ITEM# rows, PN = model, per-model "
    "ORIGIN lines); comma-aware packing TOTAL (pkg = PALLETS, GW = Gross). "
    "MEH6L040: '*' models, marks-column-aware descriptions, mixed package units "
    "(printed N PACKAGES sum). No line items → needs_gold (never pass on header only)."
)

RULES_JSON = {
    "id": "hitachi_gls_v1",
    "header": {
        "invoice_no": r"Invoice\s+No\.?\s+(MEH\w+)",
        "amount": r"GRAND TOTAL:\s+[\d,]+\s+PCS\s+J[¥￥]([\d,]+)",
        "incoterm": r"(F\.?O\.?B\.?\s+SHIMIZU)",
        "pkg": r"TOTAL\s*:\s*(\d+)\s+.*PALLETS?",
        "gw": r"TOTAL\s*:\s*\d+\s+[\d,]+\s+[\d.]+\s+([\d.]+)",
    },
}

_LINE = re.compile(
    r"^(?P<item>\d{2})\s+(?P<desc>[A-Z][A-Z0-9 /.-]*?)\s+"
    r"(?P<qty>[\d,]+)\s+PC[ES]\s+(?P<price>[\d,]+)\s+(?P<amt>[\d,]+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_PN = re.compile(r"PN:(\S+)")
# Inline accessory row (MEH6J044): "BOSCH-TW   01  PC-ALHZ1   1,000 PCS   4,302   4,302,000"
# MEH6L040: model may be "P-AP90DNA*EX" (hyphen as 2nd char, "*EX" variant suffix).
_LINE_INLINE = re.compile(
    r"(?:^|\s{2,})(?P<item>\d{2})\s+(?P<pn>[A-Z](?:[A-Z0-9]|-(?=[A-Z0-9]))[A-Z0-9/.\-*]*)\s+"
    r"(?P<qty>[\d,]+)\s+PC[ES]?\s+(?P<price>[\d,]+)\s+(?P<amt>[\d,]+)\s*$",
    re.MULTILINE,
)


def _origin_map(text: str) -> tuple[dict[str, str], str | None]:
    """``PC-AWR,PC-ARFG2-T -ORIGIN: CHINA`` / ``OTHERS -ORIGIN: JAPAN``."""
    codes = {"CHINA": "CN", "JAPAN": "JP", "THAILAND": "TH", "MALAYSIA": "MY"}
    per: dict[str, str] = {}
    other = None
    for m in re.finditer(r"^\s*([A-Z0-9][A-Z0-9,\-/.* ]*?)\s*-\s*ORIGIN:\s*([A-Z]+)", text, re.M):
        cc = codes.get(m.group(2).upper(), m.group(2).upper())
        lhs = m.group(1).strip()
        if lhs.upper() == "OTHERS":
            other = cc
        else:
            for pn in lhs.split(","):
                if pn.strip():
                    per[pn.strip().upper()] = cc
    return per, other


_PKG_UNIT = r"(?:PALLETS?|CARTONS?|CASES?|CRATES?|SKIDS?|BOXES)"


def _mixed_package_total(after_total: str, first_count: float) -> float:
    """MEH6L040: TOTAL row carries only the PALLETS count; other units follow.

    ``TOTAL : 2 ...`` / ``CARTONS`` / ``19`` / ``----`` / ``21 PACKAGES``.
    Prefer the printed ``N PACKAGES`` sum; otherwise add each extra
    unit-label + count pair to the first (TOTAL-row) count.
    """
    window = after_total.splitlines()[1 : 1 + windows.HITACHI_GLS_PKG_LINES]
    for ln in window:
        if re.search(r"\bTOTAL\s*:", ln):
            break
        m = re.match(r"^\s*([\d,]+)\s+PACKAGES?\b", ln, re.I)
        if m:
            got = us_float(m.group(1))
            if got is not None and got >= first_count:
                return float(got)
    extra = 0.0
    for a, b in zip(window, window[1:]):
        if re.search(r"\bTOTAL\s*:", a):
            break
        if re.fullmatch(r"\s*" + _PKG_UNIT + r"\s*", a, re.I):
            mb = re.fullmatch(r"\s*([\d,]+)\s*", b)
            if mb:
                extra += us_float(mb.group(1)) or 0.0
    return first_count + extra


def _row_description(lines: list[str], i: int, col: int) -> str | None:
    """Description printed under the ITEM# row, read from the item column.

    The left Marks & Numbers column (``MADE IN JAPAN``, ``P80016921``…) shares
    the same text lines, so only text at/right of the row's item column counts.
    Skip blank slices (marks-only lines); stop at the next PO / item / total.
    """
    for j in range(i + 1, min(i + windows.HITACHI_GLS_DESC_LINES, len(lines))):
        sl = lines[j][col:].strip() if len(lines[j]) > col else ""
        if not sl:
            continue
        if (
            re.match(r"P\d{6,}", sl)
            or _LINE_INLINE.search(lines[j])
            or re.search(r"TOTAL\s*:", sl, re.I)
            or sl.startswith("---")
        ):
            return None
        md = re.search(r"(ACCESSORY\s*:\s*.+?)\s*$", sl, re.I)
        if md:
            return re.sub(r"\s+", " ", md.group(1))
        if re.fullmatch(r"[A-Z][A-Z0-9 /.\-]{2,}", sl):
            return re.sub(r"\s+", " ", sl)
        return None
    return None


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "MEH" in fn or "HITACHI" in fn or "SD(TW)" in fn or "SD（TW）" in filename:
        score += 0.3
    if "GLOBAL LIFE SOLUTIONS" in text:
        score += 0.4
    if re.search(r"Invoice\s+No\.?\s+MEH", text, re.I) or re.search(
        r"Invoice\s+No\.[^\n]*\n[^\n]*?\bMEH[0-9A-Z]{4,}", text, re.I
    ):
        score += 0.25
    if "JAPANESE YEN" in text or "J¥" in text:
        score += 0.1
    if "BITZER" in text or "NIDEC TECHNO" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    # Header block: "Invoice No. … Date" label row, then the value row
    # "<consignee> <invoice no> <MON. DD, YYYY>". Read by position (value row
    # under the labels), not by a vendor prefix: MEH6xxxx and DC76K507 alike.
    date_re = r"[A-Z]{3,4}\.?\s+\d{1,2},\s+\d{4}"
    no_re = r"[A-Z]{1,6}\d[0-9A-Z-]{3,}"
    invoice_no = None
    invoice_date = None
    m_hdr_val = re.search(
        rf"Invoice\s+No\.[^\n]*\bDate\b[^\n]*\n[^\n]*?\b({no_re})\s+({date_re})[ \t]*$",
        text,
        re.I | re.M,
    )
    if m_hdr_val:
        invoice_no = m_hdr_val.group(1)
        invoice_date = en_date_to_iso(m_hdr_val.group(2))
    if not invoice_no:
        # Detail-sheet page header "Invoice No.: MEH6A036" / same-line label.
        m_inv = re.search(rf"Invoice\s+No\.?[ \t]*:?[ \t]*({no_re})\b", text, re.I)
        invoice_no = m_inv.group(1) if m_inv else None
    if invoice_no and not invoice_date:
        m_date = re.search(rf"\b{re.escape(invoice_no)}\s+({date_re})", text)
        invoice_date = en_date_to_iso(m_date.group(1)) if m_date else None
    if invoice_no and not invoice_no.upper().startswith("MEH"):
        # Read by position, but outside the series seen so far → a person checks it.
        invoice_no = fallback("invoice_no", invoice_no, "hitachi_gls:invoice_no_outside_MEH_series")

    # GRAND TOTAL carries the currency symbol: J¥ (MEH) or US$ (DC76K507).
    m_gt = re.search(
        r"GRAND TOTAL:\s+([\d,]+)\s+PCS\s+(J[¥￥]|US\$)\s*([\d,]+(?:\.\d{2})?)",
        text,
        re.I,
    )
    header_qty = us_float(m_gt.group(1)) if m_gt else None
    amount = us_float(m_gt.group(3)) if m_gt else None
    currency = "USD" if m_gt and m_gt.group(2).upper() == "US$" else "JPY"

    m_fob = re.search(r"(F\.?O\.?B\.?\s+SHIMIZU(?:\s*,\s*JAPAN)?)", text, re.I)
    incoterm = (
        re.sub(r"\s+,", ",", re.sub(r"\s+", " ", m_fob.group(1))).strip() if m_fob else None
    )

    # Packing TOTAL: "TOTAL :  16   4,815   1,646.0   1,998   25.300"
    # (PALLETS, PCS, Net KGS, Gross KGS, M3) — thousands commas allowed.
    m_pkc = re.search(
        r"(?m)^\s*TOTAL\s*:\s*(\d+)\s+([\d,]+)\s+([\d,]+(?:\.\d+)?)\s+"
        r"([\d,]+(?:\.\d+)?)\s+(\d+\.\d+)\s*$",
        text,
    )
    m_pkg = re.search(
        r"TOTAL\s*:\s*(\d+)\s+[^\n]*?([\d,]+)\s+([\d.]+)\s+([\d.]+)",
        text,
        re.I,
    )
    if m_pkc:
        pkg = float(m_pkc.group(1))
        gw = us_float(m_pkc.group(4))
    else:
        pkg = float(m_pkg.group(1)) if m_pkg else None
        gw = float(m_pkg.group(4)) if m_pkg else None
    m_tot = m_pkc or m_pkg
    if m_tot and pkg is not None:
        pkg = _mixed_package_total(text[m_tot.end():], pkg)

    origin = "JP"
    if re.search(r"ORIGIN:\s*JAPAN", text, re.I) or re.search(r"MADE IN JAPAN", text):
        origin = "JP"

    # Detail sheet often duplicated — take first block after Item# header
    items: list[Item] = []
    m_hdr = re.search(r"Item#\s+Description\s+Material", text)
    if m_hdr:
        rest = text[m_hdr.end() :]
        # stop at second Item# or packing contents duplication of same GRAND after first
        m_stop = re.search(r"GRAND TOTAL:\s+[\d,]+\s+PCS\s+J[¥￥][\d,]+", rest, re.I)
        block = rest[: m_stop.end()] if m_stop else rest[: windows.HITACHI_GLS_BLOCK_CHARS]
        lines = block.splitlines()
        for i, line in enumerate(lines):
            m = _LINE.match(line)
            if not m:
                continue
            part = None
            for j in range(i + 1, min(i + windows.HITACHI_GLS_PN_LINES, len(lines))):
                pm = _PN.search(lines[j])
                if pm:
                    part = pm.group(1)
                    break
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=part,
                    description=m.group("desc").strip(),
                    qty=us_float(m.group("qty")),
                    unit="PCS",
                    unit_price=float(m.group("price").replace(",", "")),
                    amount=float(m.group("amt").replace(",", "")),
                    origin=origin,
                    currency=currency,
                )
            )

    # Inline accessory layout (BHC 4th MEH6J044): ITEM# rows on the invoice page.
    if not items and re.search(r"\bITEM#", text):
        inv_page = re.split(r"\bPACKING\s+LIST\b", text, maxsplit=1)[0]
        m_stop = re.search(r"GRAND TOTAL:", inv_page, re.I)
        block = inv_page[: m_stop.start()] if m_stop else inv_page
        per_origin, other_origin = _origin_map(text)
        lines = block.splitlines()
        for i, line in enumerate(lines):
            m = _LINE_INLINE.search(line)
            if not m:
                continue
            # MEH6K018 spare parts: plain description below the row;
            # MEH6L040: marks column text shares those lines (column slice).
            desc = _row_description(lines, i, m.start("item"))
            pn = m.group("pn").upper()
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=pn,
                    description=desc or pn,
                    qty=us_float(m.group("qty")),
                    unit="PCS",
                    unit_price=us_float(m.group("price")),
                    amount=us_float(m.group("amt")),
                    origin=per_origin.get(pn, other_origin or origin),
                    currency=currency,
                )
            )

    if amount is None and items:
        amount = float(sum(it.amount or 0 for it in items))
    total_qty = float(sum(it.qty or 0 for it in items)) if items else header_qty

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=pkg,
        gross_weight_kg=gw,
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=total_qty,
        amount=amount,
        currency=currency,
        vendor="Hitachi Global Life Solutions, Inc.",
        origin=origin,
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="hitachi_gls_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
    )
    if m_gt:
        meta.labeled_amount = amount
        meta.labeled_amount_label = "GRAND TOTAL"
    if needs_ocr or not invoice_no or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
        if invoice_no and not items:
            meta.notes = "no line items parsed — not a pass"
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
