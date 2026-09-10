"""BITZER / BHC Versanddokument + Commercial Invoice (v1).

Adapted from BHC_HeaderExtract; trained on 3000214469 layout text.
Works with pdftotext -layout AND multiline pdfminer/pymupdf fallbacks.
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
        "origin": r"Country of origin:\s*([A-Z]{2})",
        "hs_code": r"HS-Code:\s*(\d{6,10})",
        "final_amount": r"Final amount\s+([\d.,]+)",
    },
    "items": {
        "line": r"(\d{6})\s+(\d{9})\s+(\d+)\s+PC\s+([\d.,]+)\s+EUR\s*/\s*1\s*PC\s+([\d.,]+)",
    },
}

# Single-line (pdftotext -layout) patterns
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

# Multiline (pdfminer / pymupdf) block starts: commercial lines 000001…
_ITEM_START_RE = re.compile(r"^[ \t]*(0000\d{2})\b", re.MULTILINE)
_MATERIAL_RE = re.compile(r"\b(\d{9})\b")
_PRICE_RE = re.compile(r"([\d.,]+)\s*EUR\s*/\s*1\s*PC")
_DESC_BLOCK_RE = re.compile(r"^[ \t]*((?:CSW|CSE|GSD|OSKA)\S+)", re.MULTILINE)
_EU_MONEY_RE = re.compile(r"([\d]{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})")

AMOUNT_TOL = 0.05


def _commercial_invoice_chunk(text: str) -> str:
    """Slice commercial-invoice region.

    Includes a lead-in before the ``Commercial Invoice`` heading so pymupdf
    reading-order (item block before heading on the same page) still works.
    Ends at terms/boilerplate, *after* Final amount when present.
    """
    idx = text.find("Commercial Invoice")
    if idx < 0:
        return text
    start = max(0, idx - 3000)
    # Prefer not to start mid-Ladeliste serial dump: snap forward to a blank line
    # near idx if the lead-in is huge.
    end_markers = (
        "Sales, deliveries and other services",
        "General Terms and Conditions of Sale",
    )
    end = len(text)
    for marker in end_markers:
        pos = text.find(marker, idx)
        if 0 <= pos < end:
            end = pos
    return text[start:end]


def _prefer_contiguous(rows: list[tuple[str, str, int, float, float, str | None]]):
    """Keep contiguous commercial lines 000001, 000002, … when present."""
    if not rows:
        return rows
    sorted_rows = sorted(rows, key=lambda r: r[0])
    kept: list[tuple[str, str, int, float, float, str | None]] = []
    expect = 1
    for row in sorted_rows:
        n = int(row[0])
        if n == expect:
            kept.append(row)
            expect += 1
        elif kept:
            break
    return kept if kept else sorted_rows


def _qty_before_price(block: str, price_start: int) -> int | None:
    """Parse quantity from text *before* the unit-price line (avoid `/ 1 PC`)."""
    head = block[:price_start]
    # pdfminer often inserts a blank line between qty and PC
    m = re.search(r"^[ \t]*(\d+)[ \t]*\n+[ \t]*PC\b", head, re.MULTILINE)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)[ \t]+PC\b", head)
    if m:
        return int(m.group(1))
    return None


def _parse_multiline_items(
    ci: str,
) -> list[tuple[str, str, int, float, float, str | None]]:
    starts = list(_ITEM_START_RE.finditer(ci))
    found: list[tuple[str, str, int, float, float, str | None]] = []
    seen: set[str] = set()
    for i, m in enumerate(starts):
        item_no = m.group(1)
        if item_no in seen:
            continue
        end = (
            starts[i + 1].start()
            if i + 1 < len(starts)
            else min(len(ci), m.start() + 1200)
        )
        block = ci[m.start() : end]
        price_m = _PRICE_RE.search(block)
        if not price_m:
            # Ladeliste / delivery rows lack unit price — skip
            continue
        mat_m = _MATERIAL_RE.search(block)
        qty = _qty_before_price(block, price_m.start())
        if not mat_m or qty is None:
            continue
        price = eu_float(price_m.group(1))
        after = block[price_m.end() : price_m.end() + 120]
        val_m = _EU_MONEY_RE.search(after) or re.search(r"([\d.,]+)", after)
        value = eu_float(val_m.group(1)) if val_m else round(qty * price, 2)
        desc_m = _DESC_BLOCK_RE.search(block)
        seen.add(item_no)
        found.append(
            (
                item_no,
                mat_m.group(1),
                qty,
                price,
                value,
                desc_m.group(1) if desc_m else None,
            )
        )
    return _prefer_contiguous(found)


def _parse_line_items(ci: str) -> list[tuple[str, str, int, float, float, str | None]]:
    """Extract priced commercial-invoice lines (not Ladeliste package/serial rows)."""
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
        # Skip delivery-note style item nos (000010, 000020…) when they sneak in
        # without being part of the commercial 000001… sequence — handled below.
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
    uniq = _prefer_contiguous(uniq)

    # If single-line patterns missed most rows (pdfminer/pymupdf), use multiline.
    multi = _parse_multiline_items(ci)
    if len(multi) > len(uniq):
        return multi
    if not uniq and multi:
        return multi
    return uniq


def _parse_final_amount(text: str) -> float | None:
    """Parse labeled ``Final amount`` (European ``37.041,41``), possibly multiline."""
    m = re.search(r"Final amount[ \t]+([\d.,]+)", text)
    if m:
        try:
            return eu_float(m.group(1))
        except ValueError:
            pass
    m = re.search(r"Final amount\b", text)
    if not m:
        return None
    window = text[m.end() : m.end() + 400]
    cands = _EU_MONEY_RE.findall(window)
    if not cands:
        return None
    try:
        return eu_float(cands[0])
    except ValueError:
        return None


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
        else:
            # pdfminer often splits "Gross weight" / number / "KG"
            m_gw2 = re.search(
                r"Gross weight\s*([\d.,]+)\s*KG|Gross weight[\s\S]{0,40}?([\d.,]+)[\s\S]{0,10}?KG",
                ci,
                re.I,
            )
            if m_gw2:
                gross_weight_kg = eu_float(m_gw2.group(1) or m_gw2.group(2))

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

    # Document-level origin / HS (same on each commercial line for this sample set)
    m_orig = re.search(r"Country of origin:\s*([A-Z]{2})\b", ci)
    origin = m_orig.group(1) if m_orig else None
    m_hs = re.search(r"HS-Code:\s*(\d{6,10})", ci)
    hs_code = m_hs.group(1) if m_hs else None
    if origin or hs_code:
        for it in items:
            if origin and not it.origin:
                it.origin = origin
            if hs_code and not it.hs_code:
                it.hs_code = hs_code

    line_sum = round(sum(r[4] for r in lines), 2) if lines else None
    final_amount = _parse_final_amount(ci) or _parse_final_amount(text)

    notes_parts: list[str] = []
    if doc_no:
        notes_parts.append(f"doc_no={doc_no}")

    amount = final_amount if final_amount is not None else line_sum
    amount_mismatch = False
    if (
        final_amount is not None
        and line_sum is not None
        and abs(line_sum - final_amount) > AMOUNT_TOL
    ):
        amount_mismatch = True
        notes_parts.append(
            f"line_sum={line_sum} disagrees with Final amount={final_amount}"
        )

    header = Header(
        invoice_no=invoice_no,
        invoice_date=de_date_to_iso(inv_date_raw) if inv_date_raw else None,
        total_pkg=float(packages) if packages is not None else None,
        gross_weight_kg=gross_weight_kg,
        incoterm=trade_terms,
        item_line_count=len(items) if items else None,
        total_quantity=float(sum(r[2] for r in lines)) if lines else None,
        amount=amount,
        currency=currency,
        vendor="BITZER",
        origin=origin,
        hs_code=hs_code,
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="bitzer_v1",
        confidence="conflict" if amount_mismatch else "rules",
        needs_ocr=needs_ocr,
        notes="; ".join(notes_parts) if notes_parts else None,
        labeled_amount=final_amount,
        labeled_amount_label="Final amount" if final_amount is not None else None,
    )
    if needs_ocr or not invoice_no:
        meta.confidence = "needs_gold"
        meta.needs_gold = True

    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
