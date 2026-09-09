"""Hitachi Global Life Solutions (MEH) shipping advice / invoice v1.

Trained on SD(TW)_20260126_MEH6A036 layout text.
"""

from __future__ import annotations

import re

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

NOTES = "Hitachi GLS shipping advice + invoice detail; seed from MEH6A036"

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


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "MEH" in fn or "HITACHI" in fn or "SD(TW)" in fn or "SD（TW）" in filename:
        score += 0.3
    if "GLOBAL LIFE SOLUTIONS" in text:
        score += 0.4
    if re.search(r"Invoice\s+No\.?\s+MEH", text, re.I):
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
    m_inv = re.search(r"Invoice\s+No\.?\s*:?\s*(MEH\w+)", text, re.I)
    invoice_no = m_inv.group(1) if m_inv else None

    m_date = re.search(
        r"Invoice\s+No\.[^\n]*\n[^\n]*?Date\s*\n[^\n]*?(MEH\w+)\s+([A-Z]{3}\.?\s+\d{1,2},\s+\d{4})",
        text,
        re.I,
    )
    if not m_date:
        m_date = re.search(r"(MEH\w+)\s+([A-Z]{3}\.?\s+\d{1,2},\s+\d{4})", text)
    invoice_date = en_date_to_iso(m_date.group(2)) if m_date else None

    m_gt = re.search(
        r"GRAND TOTAL:\s+([\d,]+)\s+PCS\s+J[¥￥]([\d,]+)",
        text,
        re.I,
    )
    header_qty = us_float(m_gt.group(1)) if m_gt else None
    amount = float(m_gt.group(2).replace(",", "")) if m_gt else None

    m_fob = re.search(r"(F\.?O\.?B\.?\s+SHIMIZU)", text, re.I)
    incoterm = re.sub(r"\s+", " ", m_fob.group(1)).strip() if m_fob else None

    m_pkg = re.search(
        r"TOTAL\s*:\s*(\d+)\s+[^\n]*?([\d,]+)\s+([\d.]+)\s+([\d.]+)",
        text,
        re.I,
    )
    pkg = float(m_pkg.group(1)) if m_pkg else None
    gw = float(m_pkg.group(4)) if m_pkg else None

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
        block = rest[: m_stop.end()] if m_stop else rest[:8000]
        lines = block.splitlines()
        for i, line in enumerate(lines):
            m = _LINE.match(line)
            if not m:
                continue
            part = None
            for j in range(i + 1, min(i + 3, len(lines))):
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
                    currency="JPY",
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
        currency="JPY",
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
    if needs_ocr or not invoice_no:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
