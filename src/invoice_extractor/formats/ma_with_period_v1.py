"""Robert Bosch GmbH Mobility Aftermarket invoice — material PNs *with* periods.

Aligned with VBA ``MA_PDFextractWithPeriod`` / ``MA_Declaration_withPeriod``.
Typical samples: ``INVOICE 2120….PDF`` under ``90-C*`` / ``90-M*`` folders.
"""

from __future__ import annotations

import re

from invoice_extractor.formats.ma_common import find_hs_after_item, parse_rb_packages
from invoice_extractor.schema import (
    ExtractResult,
    Header,
    Item,
    Meta,
    de_date_to_iso,
    us_float,
)

MATCH_HINTS = {
    "filename_regex": r"INVOICE\s*2120|2120\d{6}",
    "keywords": [
        "ROBERT BOSCH GmbH",
        "Document No.",
        "Goods value",
        "Material No. Idx",
    ],
}

NOTES = (
    "MA Mobility Aftermarket invoice; PN has dots (17 chars e.g. 0.445.110.564.825). "
    "VBA: MA_PDFextractWithPeriod + MA_Declaration_withPeriod. "
    "Folder heuristic: 90-C* / 90-M*."
)

RULES_JSON = {
    "id": "ma_with_period_v1",
    "header": {
        "invoice_no": r"Document\s+No\.:?\s+(\d{8,12})",
        "amount": r"Goods\s+[Vv]alue\s+([\d,.]+)",
        "currency": r"(?:Amount\s+)?(?:in\s+)?(TWD|USD|EUR|CNY)\b",
        "incoterm": r"Incoterms:\s*\n\s*([^\n]+)",
    },
    "items": {
        "line": (
            r"(\d{5})\s+(\S{10,20})\s+(.+?)\s+([\d,]+)\s+(EA|SET)\s+"
            r"([\d,]+(?:\.\d+)?)\s*\*?\s+([\d,]+(?:\.\d+)?)"
        ),
    },
}

# Require at least one dot in PN
_LINE = re.compile(
    r"^(?P<pos>\d{5})\s+(?P<pn>[A-Z0-9](?:\.[A-Z0-9]+){3,6})\s+(?P<desc>.+?)\s+"
    r"(?P<qty>[\d,]+)\s+(?P<uom>EA|SET)\s+"
    r"(?P<price>[\d,]+(?:\.\d+)?)\s*\*?\s+(?P<amt>[\d,]+(?:\.\d+)?)\s*$",
    re.MULTILINE,
)

def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "INVOICE" in fn or re.search(r"2120\d{6}", fn):
        score += 0.25
    if re.search(r"ROBERT\s+BOSCH\s+GmbH", text, re.I) and "Power Tools" not in text:
        score += 0.2
    if "Document No." in text or "Document No.:" in text:
        score += 0.1
    if re.search(r"Goods\s+[Vv]alue", text):
        score += 0.15
    # dotted PN lines are the hallmark
    if re.search(r"\d{5}\s+[A-Z0-9]\.[A-Z0-9]+\.[A-Z0-9]+", text):
        score += 0.35
    if re.search(r"\d{6}\s+[A-Z0-9]{13}\s+\S+.+\bEA\b", text) and not re.search(
        r"\d{5}\s+[A-Z0-9]\.[A-Z0-9]+\.", text
    ):
        score -= 0.45
    if "Power Tools GmbH" in text or "Net invoiced value of goods" in text:
        score -= 0.5
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    if "Bosch Home Comfort Supply" in text:
        score -= 0.5
    if "Cont.-Pers. Sales" in text and re.search(r"\bMA\b", text):
        score += 0.05
    return max(0.0, min(score, 1.0))


def _invoice_no(text: str) -> str | None:
    m = re.search(r"Document\s+No\.:?\s+(\d{8,12})", text)
    return m.group(1) if m else None


def _invoice_date(text: str) -> str | None:
    m = re.search(r"Date:\s+(\d{2}\.\d{2}\.\d{4})", text)
    return de_date_to_iso(m.group(1)) if m else None


def _goods_value(text: str) -> float | None:
    m = re.search(r"Goods\s+[Vv]alue\s+([\d,.]+)", text)
    return us_float(m.group(1)) if m else None


def _currency(text: str) -> str | None:
    """Parse currency from Amount-in-XXX style labels.

    WithPeriod invoices split the visual label across two header rows, e.g.::

        ... Price per unit        Amount
        ... Weight          Discount          in TWD

    so a strict ``Amount in TWD`` match fails. Also accept ``Amount TWD``
    on declaration pages and ``Discount … in TWD``.
    """
    patterns = (
        r"Amount\s+in\s+(TWD|USD|EUR|CNY|GBP)",
        r"Amount\s+(TWD|USD|EUR|CNY|GBP)\b",
        r"Discount\s+in\s+(TWD|USD|EUR|CNY|GBP)",
        r"\bAmount\b[\s\S]{0,120}?\bin\s+(TWD|USD|EUR|CNY|GBP)\b",
        r"\bin\s+(TWD|USD|EUR|CNY|GBP)\b",
    )
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return m.group(1).upper()
    return None


def _incoterm(text: str) -> str | None:
    m = re.search(r"Incoterms:\s*\n\s*([^\n]+)", text)
    if m:
        return m.group(1).strip()
    m = re.search(r"Incoterms:\s*([A-Z]{3}\s+[^\n]+)", text)
    return m.group(1).strip() if m else None


def _parse_coo_index(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    m = re.search(
        r"Country of origin\s+Index([\s\S]{0,5000}?)Country of origin\b",
        text,
        re.I,
    )
    if not m:
        return out
    block = m.group(1)
    for cm in re.finditer(r"([A-Za-z][A-Za-z ./-]+?)\s+(\S{3})\s*$", block, re.M):
        out[cm.group(2)] = cm.group(1).strip()
    return out


def _parse_items(
    text: str, invoice_no: str | None, currency: str | None
) -> list[Item]:
    coo_map = _parse_coo_index(text)
    items: list[Item] = []
    seen_pos: set[str] = set()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _LINE.match(line)
        if not m:
            continue
        pos = m.group("pos")
        if pos in seen_pos:
            continue
        seen_pos.add(pos)
        pn = m.group("pn")
        qty = us_float(m.group("qty"))
        price = us_float(m.group("price"))
        amt = us_float(m.group("amt"))
        desc = re.sub(r"\s{2,}", " ", m.group("desc")).strip()
        origin = None
        idx = pn.split(".")[-1] if "." in pn else pn[-3:]
        if idx in coo_map:
            origin = coo_map[idx]
        hs = find_hs_after_item(lines, i)
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
    items = _parse_items(text, invoice_no, currency)
    total_qty = sum(it.qty or 0.0 for it in items) if items else None
    pkg, gw = parse_rb_packages(text)
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
        format_id="ma_with_period_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="Goods value",
    )
    if needs_ocr or not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
