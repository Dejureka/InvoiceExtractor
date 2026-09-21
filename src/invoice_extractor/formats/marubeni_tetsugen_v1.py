"""Marubeni Tetsugen Metals — commercial invoice + packing list v1 (OCR-friendly).

BHC case2 scan: ``(JCH26-08M1) Invoice, PL.pdf`` (empty text layer).
Combined INV+PKL; copper tube lines keyed by EMCP-P… PO / work nos.
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
    "filename_regex": r"JCH\d{2}-\d{2}M\d|Marubeni|Tetsugen",
    "keywords": [
        "MARUBENI TETSUGEN",
        "COPPER TUBE",
        "FOB NAGOYA",
        "THERMOEXCEL",
    ],
}

NOTES = (
    "Marubeni Tetsugen Metals combined INV+PL. Trained on OCR of BHC case2 "
    "(JCH26-08M1) Invoice, PL.pdf. Do not confuse filename JCH* with NIDEC."
)

RULES_JSON = {
    "id": "marubeni_tetsugen_v1",
    "header": {
        "invoice_no": r"INVOICE\s+(JCH[\w-]+)",
        "amount": r"Total\s+\d+\s+CASE\s+[\d,]+\s+PCS\s+US\$\s*([\d,]+\.\d{2})",
        "incoterm": r"(FOB\s+NAGOYA(?:,\s*JAPAN)?)",
        "pkg": r"Total\s+(\d+)\s+CASE",
        "gw": r"TOTAL\s+\d+\s+CASE\s+[\d,]+\s+PCS\s+[\d,]+\.?\d*\s+kgs\s+([\d,]+\.?\d*)\s+kgs",
    },
}

_LINE = re.compile(
    r"(?P<pn>EMCP-P\d+)\s+(?P<qty>[\d,]+)\s+PCS\s+@?US\$?\s*(?P<price>[\d.]+)\s+US\$\s*(?P<amt>[\d,]+\.\d{2})",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "MARUBENI" in fn or "TETSUGEN" in fn:
        score += 0.35
    if re.search(r"JCH\d{2}-\d{2}M", fn):
        score += 0.25
    tu = text.upper()
    if "MARUBENI TETSUGEN" in tu or "MARUBENI TETSUGEN METALS" in tu:
        score += 0.5
    if "COPPER TUBE" in tu and "THERMOEXCEL" in tu:
        score += 0.15
    if "FOB NAGOYA" in tu:
        score += 0.1
    if "NIDEC TECHNO" in tu or "BITZER" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    inv_part = re.split(r"PACKING\s+LIST", text, maxsplit=1, flags=re.I)[0]

    m_inv = re.search(r"INVOICE\s+(JCH[\w-]+)", inv_part, re.I)
    if not m_inv:
        m_inv = re.search(r"\b(JCH\d{2}-\d{2}M\d+)\b", inv_part, re.I)
    invoice_no = m_inv.group(1).upper() if m_inv else None

    m_date = re.search(
        r"(?:Tokyo|TOKYO)\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})",
        inv_part,
        re.I,
    )
    invoice_date = en_date_to_iso(m_date.group(1)) if m_date else None

    amount = None
    m_amt = re.search(
        r"Total\s+(\d+)\s+CASE\s+([\d,]+)\s+PCS\s+US\$\s*([\d,]+\.\d{2})",
        inv_part,
        re.I,
    )
    total_pkg = None
    total_qty = None
    if m_amt:
        total_pkg = float(m_amt.group(1))
        total_qty = us_float(m_amt.group(2))
        amount = us_float(m_amt.group(3))

    incoterm = None
    m_inc = re.search(r"(FOB\s+NAGOYA(?:,\s*JAPAN)?)", inv_part, re.I)
    if m_inc:
        incoterm = re.sub(r"\s+", " ", m_inc.group(1)).upper()

    items: list[Item] = []
    for m in _LINE.finditer(inv_part):
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=m.group("pn").upper(),
                description="COPPER TUBE (THERMOEXCEL CPC)",
                qty=us_float(m.group("qty")),
                unit="PCS",
                unit_price=us_float(m.group("price")),
                amount=us_float(m.group("amt")),
                origin="Japan",
                currency="USD",
            )
        )

    gw = None
    # Prefer packing TOTAL gross weight
    m_gw = re.search(
        r"TOTAL\s+\d+\s+CASE\s+[\d,]+\s+PCS\s+([\d,]+\.?\d*)\s+kgs\s+([\d,]+\.?\d*)\s+kgs",
        text,
        re.I,
    )
    if m_gw:
        try:
            gw = us_float(m_gw.group(2))
        except ValueError:
            gw = None
        if total_pkg is None:
            # already have from invoice total line
            pass

    if total_qty is None and items:
        total_qty = sum(i.qty or 0 for i in items)
    if amount is None and items:
        amount = round(sum(i.amount or 0 for i in items), 2)

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=total_pkg,
        gross_weight_kg=gw,
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=total_qty,
        amount=amount,
        currency="USD",
        vendor="Marubeni Tetsugen Metals Corporation",
        origin="Japan",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="marubeni_tetsugen_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="Total",
        source="combined",
    )
    if needs_ocr or not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
