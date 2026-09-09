"""Robert Bosch Power Tools GmbH (PT / Gloria) invoice v1.

Regex trained from **pdftotext -layout** of Round1 PT GmbH sample PDFs
(not paste-shaped VBA alone). VBA PT_PDFextract / PT_AddInvFromGloria used
as field-name reference only.
"""

from __future__ import annotations

import re
from typing import Any

from invoice_extractor.schema import (
    ExtractResult,
    Header,
    Item,
    Meta,
    de_date_to_iso,
    us_float,
)

MATCH_HINTS = {
    "filename_regex": r"50\d{6}|PT\s*GmbH|Gloria",
    "keywords": [
        "Robert Bosch Power Tools GmbH",
        "Invoice No.",
        "Net invoiced value of goods",
        "Material no.",
    ],
}

NOTES = (
    "PT GmbH / Gloria commercial invoice; layout-trained from msg_extract PDFs "
    "(50656407 etc.). Amounts US-style; currency from Value:/column header USD."
)

RULES_JSON = {
    "id": "pt_gloria_v1",
    "header": {
        "invoice_no": r"Invoice\s+No\.\s+(\d{6,12})",
        "invoice_date": r"Invoice\s+Date\s+(\d{2}\.\d{2}\.\d{4})",
        "amount": r"Net\s+invoiced\s+value\s+of\s+goods\s+([\d,]+\.\d{2})",
        "incoterm": r"\b(FCA|FOB|CIF|CIP|EXW|DDP|DAP|CFR)\b\s+([^\n*]+)",
        "currency_value": r"Value:\s+[\d,.]+\s+(\w+)",
        "gross_weight_total": r"^\s*total\s+([\d.]+)\s*KG\s+([\d,.]+)\s+\w+",
        "pkg_summary": r"^.{0,20}(.+?)\s+:\s+(\d+)\s*$",
    },
    "items": {
        # material like 1.600.A01.2FZ or 0.601.076.800 then desc... qty pcs price amount
        "line": (
            r"(\d\.\d{3}\.[A-Z0-9]{3}\.[A-Z0-9]{2,3})"
            r"\s+(.+?)\s+(\d[\d,]*)\s+pcs\s+([\d,.]+)\s+([\d,.]+)"
        ),
        "origin_hs": r"^\s*(?:[A-Z]{2}\s+)?([A-Z]{2})\s+(\d{6,10})\s+",
    },
}

# Material no. pattern: digit.ddd.xxx.xxx (Bosch style)
_MAT_LINE = re.compile(
    r"(?P<mat>\d\.\d{3}\.[A-Za-z0-9]{3}\.[A-Za-z0-9]{2,3})"
    r"\s+(?P<rest>.+?)\s+"
    r"(?P<qty>\d{1,3}(?:,\d{3})*)\s+pcs\s+"
    r"(?P<price>\d[\d,]*\.\d{2})\s+"
    r"(?P<amt>\d[\d,]*\.\d{2})",
    re.IGNORECASE,
)

_ORIGIN_HS = re.compile(
    r"^\s*(?:\d+\s+)?"  # optional packing no leftover
    r"(?P<origin>[A-Z]{2})\s+(?P<hs>\d{6,10})\b",
    re.MULTILINE,
)

_PKG_SUMMARY = re.compile(
    r"^\s*(?P<label>(?:P\.\d+\s+)?(?:Folding Box|CARTON|Pallet|Euro Pallet|CARTON\s*-?\w*)[^\n:]*?)"
    r"\s+:\s+(?P<n>\d+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

# Also count packing lines: "1 P.13 Folding Box..." or "1 CARTON"
_PKG_LINE = re.compile(
    r"^\s*\d+/\s+(\d+)\s+(?:P\.\d+\s+)?(?:Folding|CARTON|Pallet|Euro)",
    re.MULTILINE | re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if re.search(r"50\d{6}", fn) or "PT" in fn or "GMBH" in fn:
        score += 0.25
    if "Robert Bosch Power Tools GmbH" in text:
        score += 0.45
    if re.search(r"Invoice\s+No\.", text):
        score += 0.15
    if "Net invoiced value of goods" in text:
        score += 0.15
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _first_invoice_no(text: str) -> str | None:
    # Prefer the right-side header form from pdftotext -layout
    m = re.search(r"Invoice\s+No\.\s+(\d{6,12})", text)
    return m.group(1) if m else None


def _first_invoice_date(text: str) -> str | None:
    m = re.search(r"Invoice\s+Date\s+(\d{2}\.\d{2}\.\d{4})", text)
    return de_date_to_iso(m.group(1)) if m else None


def _amount(text: str) -> float | None:
    m = re.search(
        r"Net\s+invoiced\s+value\s+of\s+goods\s+([\d,]+\.\d{2})",
        text,
    )
    if m:
        return us_float(m.group(1))
    m = re.search(r"Discountable\s+amount\s+([\d,]+\.\d{2})", text)
    if m:
        return us_float(m.group(1))
    m = re.search(r"Total\s+([\d,]+\.\d{2})\s+\*\*", text)
    if m:
        return us_float(m.group(1))
    return None


def _currency(text: str) -> str | None:
    m = re.search(r"Value:\s+[\d,.]+\s+(\w+)", text)
    if m:
        return m.group(1)
    # column header "USD            USD" near Total amount
    m = re.search(
        r"Price\s+Total amount.*\n.*?\b(USD|EUR|CNY|GBP)\b",
        text,
        re.I,
    )
    if m:
        return m.group(1).upper()
    if re.search(r"\bUSD\b", text) and not re.search(r"Currency\s+EUR", text):
        return "USD"
    return None


def _incoterm(text: str) -> str | None:
    m = re.search(
        r"\b(FCA|FOB|CIF|CIP|EXW|DDP|DAP|CFR)\b[ \t]+([A-Za-z][^\n*]{0,40})",
        text,
    )
    if not m:
        return None
    place = m.group(2).strip()
    return f"{m.group(1)} {place}".strip()


def _gross_weight(text: str) -> float | None:
    # tariff summary: total     340.394 KG    10,091.68  USD
    m = re.search(
        r"^\s*total\s+([\d.]+)\s*KG\s+([\d,.]+)\s+\w+",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if m:
        return float(m.group(1))
    m = re.search(r"Gross\s+Weight\S*\s+([\d.]+)\s*KG", text, re.I)
    if m:
        return float(m.group(1))
    # packing footer totals line: 340.394 kg                437.530 kg
    m = re.search(
        r"^\s*([\d.]+)\s*kg\s+([\d.]+)\s*kg\s*$",
        text,
        re.MULTILINE | re.I,
    )
    if m:
        return float(m.group(2))  # gross is usually second
    return None


def _total_pkg(text: str) -> float | None:
    total = 0
    found = False
    for m in _PKG_SUMMARY.finditer(text):
        total += int(m.group("n"))
        found = True
    if found:
        return float(total)
    # fallback: sum first number on packing detail lines
    for m in _PKG_LINE.finditer(text):
        total += int(m.group(1))
        found = True
    return float(total) if found else None


def _parse_items(text: str, invoice_no: str | None, currency: str | None) -> list[Item]:
    items: list[Item] = []
    # Deduplicate exact repeated line strings only (page chrome), keep same
    # part_no/qty/amount when they are distinct deliveries.
    seen_lines: set[str] = set()
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _MAT_LINE.search(line)
        if not m:
            continue
        # skip packing-list style lines that also contain material patterns rarely
        if "Folding Box" in line or "CARTON" in line and "pcs" not in line.lower():
            continue
        norm = " ".join(line.split())
        if norm in seen_lines:
            continue
        seen_lines.add(norm)
        mat = m.group("mat")
        qty = us_float(m.group("qty"))
        price = us_float(m.group("price"))
        amt = us_float(m.group("amt"))

        rest = m.group("rest").strip()
        # rest often has two description columns jammed; take first ~40 chars chunk
        desc = re.sub(r"\s{2,}", " ", rest).strip()
        # trim if still has trailing second desc — keep reasonable length
        if len(desc) > 80:
            desc = desc[:80].rsplit(" ", 1)[0]

        origin = None
        hs = None
        # look ahead 1-3 lines for origin/HS
        for j in range(i + 1, min(i + 4, len(lines))):
            om = re.search(
                r"\b([A-Z]{2})\s+(\d{8,10})\b",
                lines[j],
            )
            if om:
                origin, hs = om.group(1), om.group(2)
                break

        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=mat,
                description=desc or None,
                qty=qty,
                unit="pcs",
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
    invoice_no = _first_invoice_no(text)
    invoice_date = _first_invoice_date(text)
    amount = _amount(text)
    currency = _currency(text)
    incoterm = _incoterm(text)
    gw = _gross_weight(text)
    pkg = _total_pkg(text)
    items = _parse_items(text, invoice_no, currency)

    total_qty = sum(it.qty or 0.0 for it in items) if items else None
    # Prefer summing items for line count
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
        vendor="Robert Bosch Power Tools GmbH",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="pt_gloria_v1",
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
