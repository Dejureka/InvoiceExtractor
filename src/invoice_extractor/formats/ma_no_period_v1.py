"""Robert Bosch GmbH Mobility Aftermarket invoice — material PNs *without* periods.

Aligned with VBA ``MA_PDFextract_NoPeriod`` / ``MA_Declaration_noPeriod``.
Typical samples: ``*_*_RBTW_*.PDF`` under 90-S* / 90-KWE* folders.
Layout-trained from pdftotext -layout (not paste-shaped VBA alone).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import (
    ExtractResult,
    Header,
    Item,
    Meta,
    de_date_to_iso,
    us_float,
)

MATCH_HINTS = {
    "filename_regex": r"RBTW|2000\d{6}",
    "keywords": [
        "Robert BOSCH GmbH",
        "Document No.",
        "Goods Value",
        "Material No.",
    ],
}

NOTES = (
    "MA Mobility Aftermarket system invoice; PN is 13-char without dots "
    "(e.g. 0445110594879). VBA: MA_PDFextract_NoPeriod + MA_Declaration_noPeriod. "
    "Folder heuristic: not 90-C*/90-M*."
)

RULES_JSON = {
    "id": "ma_no_period_v1",
    "header": {
        "invoice_no": r"Document\s+No\.:?\s+(\d{8,12})",
        "amount": r"Goods\s+Value\s+([\d,.]+)",
        "incoterm": r"Incoterms:\s*\n\s*([^\n]+)",
        "currency": r"Amount in\s+\w*\s*(TWD|USD|EUR|CNY)",
    },
    "items": {
        "line": (
            r"(\d{5,6})\s+([A-Z0-9]{13})\s+(.+?)\s+"
            r"([\d,]+)\s+(EA|SET)\s+([\d,]+\.\d{2})\s*\*\s+([\d,]+(?:\.\d{2})?)"
        ),
    },
}

_LINE = re.compile(
    r"^(?P<pos>\d{5,6})\s+(?P<pn>[A-Z0-9]{13})\s+(?P<desc>.+?)\s+"
    r"(?P<qty>[\d,]+)\s+(?P<uom>EA|SET)\s+"
    r"(?P<price>[\d,]+\.\d{2})\s*\*\s+(?P<amt>[\d,]+(?:\.\d{2})?)\s*$",
    re.MULTILINE,
)

_HS = re.compile(r"HS\s*CODE\s+(\d{6,12})", re.I)
_WEIGHT = re.compile(r"Weight\s+([\d,.]+)\s*KG", re.I)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "RBTW" in fn or re.search(r"2000\d{6}", fn):
        score += 0.3
    if re.search(r"Robert\s+BOSCH\s+GmbH", text, re.I) and "Power Tools" not in text:
        score += 0.25
    if "Document No." in text or "Document No.:" in text:
        score += 0.15
    if re.search(r"Goods\s+Value", text):
        score += 0.15
    # dotted MA PNs → this is the other variant
    if re.search(r"\d{5}\s+\d\.\d{3}\.\d{3}\.", text):
        score -= 0.45
    if "Power Tools GmbH" in text or "Net invoiced value of goods" in text:
        score -= 0.5
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    if "Bosch Home Comfort Supply" in text:
        score -= 0.5
    # strong: 6-digit pos + 13-char undotted PN
    if re.search(r"\d{6}\s+[A-Z0-9]{13}\s+\S+.+\bEA\b", text):
        score += 0.25
    return max(0.0, min(score, 1.0))


def _invoice_no(text: str) -> str | None:
    m = re.search(r"Document\s+No\.:?\s+(\d{8,12})", text)
    return m.group(1) if m else None


def _invoice_date(text: str) -> str | None:
    m = re.search(r"Date:\s+(\d{2}\.\d{2}\.\d{4})", text)
    return de_date_to_iso(m.group(1)) if m else None


def _goods_value(text: str) -> float | None:
    m = re.search(r"Goods\s+Value\s+([\d,.]+)", text)
    return us_float(m.group(1)) if m else None


def _currency(text: str) -> str | None:
    m = re.search(
        r"Amount in\s+[^\n]{0,40}?\b(TWD|USD|EUR|CNY|GBP)\b",
        text,
        re.I,
    )
    if m:
        return m.group(1).upper()
    m = re.search(r"\bAmount in\b[\s\S]{0,80}?\b(TWD|USD|EUR)\b", text)
    return m.group(1).upper() if m else None


def _incoterm(text: str) -> str | None:
    m = re.search(r"Incoterms:\s*\n\s*([^\n]+)", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"Incoterms:\s*([A-Z]{3}\s+[^\n]+)", text)
    return m.group(1).strip() if m else None


def _gross_weight(text: str) -> float | None:
    """Prefer packing-summary Gross totals near end (Carton/Pallet rows)."""
    # Final summary style: "37 Carton Generic ... Gross 1247.980 KG"
    rows = re.findall(
        r"(?:Carton|Pallet|Package)[^\n]{0,80}?Gross\s+([\d,.]+)\s*KG",
        text,
        re.I,
    )
    if rows:
        # use last contiguous block of such rows (summary page)
        return round(sum(us_float(x) for x in rows[-12:]), 3)
    return None


def _total_pkg(text: str) -> float | None:
    rows = re.findall(
        r"^\s*(\d+)\s+(?:Carton|Pallet)\b",
        text,
        re.M | re.I,
    )
    if rows:
        return float(sum(int(x) for x in rows[-12:]))
    return None


def _parse_coo_index(text: str) -> dict[str, str]:
    """Map 3-char index → country name from 'Country Of Origin Index' block."""
    out: dict[str, str] = {}
    m = re.search(
        r"Country\s+Of\s+Origin\s+Index([\s\S]{0,4000}?)Country\s+Of\s+Origin\b",
        text,
        re.I,
    )
    if not m:
        return out
    block = m.group(1)
    # paste-shaped often: country\nIDX ; layout may be "Germany 000"
    for cm in re.finditer(r"([A-Za-z][A-Za-z ./-]+?)\s+(\S{3})\s*$", block, re.M):
        out[cm.group(2)] = cm.group(1).strip()
    return out


def _parse_items(
    text: str, invoice_no: str | None, currency: str | None
) -> list[Item]:
    coo_map = _parse_coo_index(text)
    items: list[Item] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _LINE.match(line)
        if not m:
            continue
        pn = m.group("pn")
        qty = us_float(m.group("qty"))
        price = us_float(m.group("price"))
        amt = us_float(m.group("amt"))
        desc = re.sub(r"\s{2,}", " ", m.group("desc")).strip()
        hs = None
        origin = None
        idx = pn[-3:] if len(pn) >= 3 else ""
        if idx in coo_map:
            origin = coo_map[idx]
        for j in range(i + 1, min(i + 8, len(lines))):
            hm = _HS.search(lines[j])
            if hm and hs is None:
                hs = hm.group(1)
            if re.match(r"^\s*\d{5,6}\s+[A-Z0-9]{13}\b", lines[j]):
                break
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=pn,
                description=desc or None,
                qty=qty,
                unit=m.group("uom"),
                unit_price=price,
                amount=amt,
                origin=origin,
                hs_code=hs,
                currency=currency,
            )
        )
    return items


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    invoice_no = _invoice_no(text)
    invoice_date = _invoice_date(text)
    amount = _goods_value(text)
    currency = _currency(text)
    incoterm = _incoterm(text)
    gw = _gross_weight(text)
    pkg = _total_pkg(text)
    items = _parse_items(text, invoice_no, currency)
    total_qty = sum(it.qty or 0.0 for it in items) if items else None
    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=pkg,
        gross_weight_kg=gw,
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=float(total_qty) if total_qty is not None else None,
        amount=amount,
        currency=currency,
        vendor="Robert Bosch GmbH (MA)",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="ma_no_period_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="Goods Value",
    )
    if needs_ocr or not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
