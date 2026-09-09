"""HIGHLY International (Hong Kong) invoice v1.

Trained on 台湾博世 26020900066 DOCS layout text.
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
    "filename_regex": r"260209|HIGHLY|海立|台湾博世",
    "keywords": [
        "HIGHLY INTERNATIONAL",
        "海立国际",
        "AIR CONDITIONER COMPRESSOR",
        "INV#",
    ],
}

NOTES = "HIGHLY International (HK) bilingual invoice; seed from 26020900066"

RULES_JSON = {
    "id": "highly_v1",
    "header": {
        "invoice_no": r"(?:INV#:?|/INV#:)\s*(\d{8,14})",
        "amount": r"TOTAL:\s+\d+\s+PACKAGES\s+[\d,]+\s+SETS\s+USD\s+([\d,.]+)",
        "incoterm": r"(FOB\s+SHANGHAI)",
        "pkg": r"TOTAL:\s+(\d+)\s+PACKAGES",
        "gw": r"TOTAL:\s+\d+\s+PACKAGES\s+[\d,]+\s+SETS\s+[\d,.]+\s+KGS\s+([\d,.]+)\s+KGS",
    },
}

_LINE = re.compile(
    r"(?P<po>P\d+)\s+MODEL\s+(?P<model>\S+)\s+(?P<qty>\d+)\s+SETS\s+"
    r"USD\s+(?P<price>[\d.]+)\s+USD\s+(?P<amt>[\d,.]+)",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "HIGHLY" in fn or "海立" in filename or "260209" in fn:
        score += 0.3
    if "HIGHLY INTERNATIONAL" in text or "海立国际" in text:
        score += 0.5
    if re.search(r"/INV#:", text) or re.search(r"INV#:", text):
        score += 0.15
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
    # Prefer invoice page before packing list
    ci = text.split("PACKING LIST")[0]

    m_inv = re.search(r"(?:/INV#:|INV#:)\s*(\d{8,14})", text)
    if not m_inv:
        m_inv = re.search(r"发票号\s*/INV#:\s*(\d{8,14})", text)
    invoice_no = m_inv.group(1) if m_inv else None

    m_date = re.search(r"(?:日期/DATE:|DATE:)\s*([A-Za-z]+\s+\d{1,2},\s+\d{4})", text)
    invoice_date = en_date_to_iso(m_date.group(1)) if m_date else None

    m_tot = re.search(
        r"TOTAL:\s+(\d+)\s+PACKAGES\s+([\d,]+)\s+SETS\s+USD\s+([\d,.]+)",
        ci,
        re.I,
    )
    pkg = float(m_tot.group(1)) if m_tot else None
    header_qty = us_float(m_tot.group(2)) if m_tot else None
    amount = us_float(m_tot.group(3)) if m_tot else None

    # Packing list gross weight
    pl = text[text.find("PACKING LIST") :] if "PACKING LIST" in text else ""
    m_gw = re.search(
        r"TOTAL:\s+\d+\s+PACKAGES\s+[\d,]+\s+SETS\s+([\d,.]+)\s+KGS\s+([\d,.]+)\s+KGS",
        pl,
        re.I,
    )
    gw = us_float(m_gw.group(2)) if m_gw else None
    if pkg is None and m_gw:
        m_pkg2 = re.search(r"TOTAL:\s+(\d+)\s+PACKAGES", pl, re.I)
        if m_pkg2:
            pkg = float(m_pkg2.group(1))

    m_fob = re.search(r"(FOB\s+SHANGHAI)", text, re.I)
    incoterm = m_fob.group(1).strip() if m_fob else None

    items: list[Item] = []
    for m in _LINE.finditer(ci):
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=m.group("model"),
                description=f"MODEL {m.group('model')} (PO {m.group('po')})",
                qty=us_float(m.group("qty")),
                unit="SETS",
                unit_price=us_float(m.group("price")),
                amount=us_float(m.group("amt")),
                currency="USD",
            )
        )

    if amount is None and items:
        amount = round(sum(it.amount or 0 for it in items), 2)
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
        currency="USD",
        vendor="HIGHLY INTERNATIONAL (HONG KONG) LIMITED",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="highly_v1",
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
