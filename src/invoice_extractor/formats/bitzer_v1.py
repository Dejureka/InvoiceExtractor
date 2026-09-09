"""BITZER / BHC Versanddokument + Commercial Invoice (v1).

Adapted from BHC_HeaderExtract; trained on 3000214469 layout text.
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
    eu_float,
)

MATCH_HINTS = {
    "filename_regex": r"3000\d+|BITZER|Versanddokument|BHC",
    "keywords": ["BITZER", "Ladeliste", "Commercial Invoice", "Kühlmaschinenbau"],
}

NOTES = "BITZER Kühlmaschinenbau Versanddokument + Commercial Invoice; seed from BHC_HeaderExtract"

RULES_JSON = {
    "id": "bitzer_v1",
    "header": {
        "invoice_no": r"(?:Number\s*/\s*Doc\.\s*date|Commercial Invoice)[\s\S]{0,200}?(\d{6,12})\s*/\s*(\d{2}\.\d{2}\.\d{4})",
        "currency": r"Currency\s+(\w+)",
        "packages": r"Gesamtgewicht\s+(\d+)\s+([\d.,]+)\s*KG",
        "gross_weight": r"Gross weight\s+([\d.,]+)\s*KG",
        "terms": r"Terms:\s*([^\n]+)",
    },
    "items": {
        "line": r"(\d{6})\s+(\d{9})\s+(\d+)\s+PC\s+([\d.,]+)\s+EUR\s*/\s*1\s*PC\s+([\d.,]+)",
    },
}

_LINE_RE = re.compile(
    r"(\d{6})\s+(\d{9})\s+(\d+)\s+PC\s+([\d.,]+)\s+EUR\s*/\s*1\s*PC\s+([\d.,]+)",
    re.MULTILINE,
)
_LINE_RE_LOOSE = re.compile(
    r"(\d{6})\s+(\d{9})[\s\S]{0,80}?(\d+)\s+PC[\s\S]{0,40}?"
    r"([\d.,]+)\s+EUR\s*/\s*1\s*PC\s+([\d.,]+)"
)
_DESC_RE = re.compile(
    r"^(\d{6})\s+(\d{9})\s+(\d+)\s+PC\s+([\d.,]+)\s+EUR\s*/\s*1\s*PC\s+([\d.,]+)\s*\n"
    r"\s+([^\n]+)",
    re.MULTILINE,
)


def _commercial_invoice_chunk(text: str) -> str:
    idx = text.find("Commercial Invoice")
    if idx < 0:
        return text
    end_markers = (
        "Performance date corresponds to invoice date",
        "Sales, deliveries and other services",
        "General Terms and Conditions of Sale",
    )
    end = len(text)
    for marker in end_markers:
        pos = text.find(marker, idx)
        if 0 <= pos < end:
            end = pos
    return text[idx:end]


def _parse_line_items(ci: str) -> list[tuple[str, str, int, float, float, str | None]]:
    found: list[tuple[str, str, str, str, str]] = []
    for m in _LINE_RE.finditer(ci):
        found.append(m.groups())
    tight = {g[0] for g in found}
    for m in _LINE_RE_LOOSE.finditer(ci):
        g = m.groups()
        if g[0] not in tight:
            found.append(g)
            tight.add(g[0])

    desc_map: dict[str, str] = {}
    for m in _DESC_RE.finditer(ci):
        desc_map[m.group(1)] = m.group(6).strip()

    seen: set[str] = set()
    uniq: list[tuple[str, str, int, float, float, str | None]] = []
    for item, material, qty, price, value in found:
        if item in seen:
            continue
        seen.add(item)
        uniq.append(
            (
                item,
                material,
                int(qty),
                eu_float(price),
                eu_float(value),
                desc_map.get(item),
            )
        )
    uniq.sort(key=lambda r: r[0])
    return uniq


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "BITZER" in fn or "VERSAND" in fn or re.search(r"3000\d{6}", fn):
        score += 0.4
    if "BITZER" in text:
        score += 0.4
    if "Ladeliste" in text:
        score += 0.15
    if "Commercial Invoice" in text and "BITZER" in text:
        score += 0.2
    return min(score, 1.0)


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    m_lade = re.search(
        r"Ladeliste[\s\S]*?(\d{10})\s*/\s*(\d{2}\.\d{2}\.\d{4})",
        text,
    )
    doc_no = m_lade.group(1) if m_lade else None
    if not doc_no:
        m_alt = re.search(r"^[\s]*(\d{10})\s*/\s*(\d{2}\.\d{2}\.\d{4})", text, re.M)
        if m_alt:
            doc_no = m_alt.group(1)

    ci = _commercial_invoice_chunk(text)
    m_inv = re.search(
        r"(?:Number\s*/\s*Doc\.\s*date\s*/\s*Print\s*date|Commercial Invoice)"
        r"[\s\S]{0,200}?(\d{6,12})\s*/\s*(\d{2}\.\d{2}\.\d{4})",
        ci,
        re.I,
    )
    if not m_inv:
        m_inv = re.search(
            r"(\d{6,12})\s*/\s*(\d{2}\.\d{2}\.\d{4})\s*/\s*(\d{2}\.\d{2}\.\d{4})",
            ci,
        )
    invoice_no = m_inv.group(1) if m_inv else None
    inv_date_raw = m_inv.group(2) if m_inv else None

    m_curr = re.search(r"Currency\s+(\w+)", ci)
    currency = m_curr.group(1) if m_curr else "EUR"

    m_pkg = re.search(r"Gesamtgewicht\s+(\d+)\s+([\d.,]+)\s*KG", text)
    packages = int(m_pkg.group(1)) if m_pkg else None
    gross_weight_kg = eu_float(m_pkg.group(2)) if m_pkg else None
    if gross_weight_kg is None:
        m_gw = re.search(r"Gross weight\s+([\d.,]+)\s*KG", ci)
        if m_gw:
            gross_weight_kg = eu_float(m_gw.group(1))

    m_terms = re.search(r"Terms:\s*([^\n]+)", ci)
    if m_terms:
        trade_terms = m_terms.group(1).strip()
    else:
        m_tod = re.search(r"Terms of delivery\s+([^\n]+)", text)
        trade_terms = m_tod.group(1).strip() if m_tod else None

    lines = _parse_line_items(ci)
    items: list[Item] = []
    for _item_no, material, qty, price, value, desc in lines:
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=material,
                description=desc,
                qty=float(qty),
                unit="PC",
                unit_price=price,
                amount=value,
                currency=currency,
            )
        )

    header = Header(
        invoice_no=invoice_no,
        invoice_date=de_date_to_iso(inv_date_raw) if inv_date_raw else None,
        total_pkg=float(packages) if packages is not None else None,
        gross_weight_kg=gross_weight_kg,
        incoterm=trade_terms,
        item_line_count=len(items) if items else None,
        total_quantity=float(sum(r[2] for r in lines)) if lines else None,
        amount=round(sum(r[4] for r in lines), 2) if lines else None,
        currency=currency,
        vendor="BITZER",
    )
    # stash doc_no in notes via meta
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="bitzer_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        notes=f"doc_no={doc_no}" if doc_no else None,
    )
    if needs_ocr or not invoice_no:
        meta.confidence = "needs_gold"
        meta.needs_gold = True

    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
