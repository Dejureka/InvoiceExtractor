"""Shanghai Nature International Trading — commercial invoice v1 (OCR-friendly).

BHC case7 scan: ``invoice309.pdf`` / ``packing309.pdf`` (empty text layer).
Invoice no. pattern ``NBT###``; lines are HEATING BELT / part codes ``2EH…`` / ``3EH…``.
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
    "filename_regex": r"invoice309|packing309|NBT\d+",
    "keywords": [
        "SHANGHAI NATURE INTERNATIONAL TRADING",
        "HEATING BELT",
        "NBT",
        "FOB SHANGHAI",
    ],
}

NOTES = (
    "Shanghai Nature INV/PKL (heating belt). Trained on OCR of case7 invoice309/packing309. "
    "Soft-missing GW OK when PKL OCR is noisy; packages often 1 pallet."
)

RULES_JSON = {
    "id": "shanghai_nature_v1",
    "header": {
        "invoice_no": r"NO[:\s]*([A-Z]{2,4}\d{2,6})",
        "amount": r"(?:TOTAL|Torau|Tota[lI])[:\s|]*[\d,.\s]*([\d,]+\.\d{2})",
        "incoterm": r"(FOB\s+SHANGHAI)",
        "currency": "USD",
    },
}

# OCR may garble headers; match part-code lines with qty/price/amount
_LINE = re.compile(
    r"(?P<pn>[23]EH[0-9O]{4,6}[A-Z]?)\s+"
    r"(?:P?(?P<po>P?\d{7,12})\s+)?"
    r"(?P<qty>[\d,]+)\s+"
    r"(?P<price>\d+\.\d{2})\s+"
    r"(?P<amt>[\d,]+\.\d{2})",
    re.IGNORECASE,
)

_LINE_WITH_DESC = re.compile(
    r"(?:HEATING\s+BELT\s+)?(?P<pn>[23]EH[0-9O]{4,6}[A-Z]?)\s+"
    r"(?P<po>P\d{7,12})\s+"
    r"(?P<qty>[\d,]+)\s+"
    r"(?P<price>\d+\.\d{2})\s+"
    r"(?P<amt>[\d,]+\.\d{2})",
    re.IGNORECASE,
)


def _fix_ocr_pn(pn: str) -> str:
    # OCR sometimes reads 0 as O inside codes; keep alnum upper
    return pn.upper().replace("O", "0") if re.match(r"[23]EHO", pn.upper()) else pn.upper()


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "NBT" in fn or "309" in fn and ("INVOICE" in fn or "PACKING" in fn):
        score += 0.2
    if "SHANGHAI NATURE" in text.upper():
        score += 0.55
    if "HEATING BELT" in text.upper():
        score += 0.15
    if re.search(r"\bNBT\d+\b", text, re.I) or re.search(r"NO[:\s]*NBT", text, re.I):
        score += 0.15
    if "MARUBENI" in text.upper() or "NIDEC TECHNO" in text.upper():
        score -= 0.5
    if "Bosch Home Comfort Supply" in text and "NATURE" not in text.upper():
        score -= 0.3
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    inv_part = text.split("PACKING LIST")[0]

    m_inv = re.search(r"NO[:\s]*([A-Z]{2,4}\d{2,6})", inv_part, re.I)
    if not m_inv:
        m_inv = re.search(r"\b(NBT\d+)\b", inv_part, re.I)
    invoice_no = m_inv.group(1).upper() if m_inv else None

    m_date = re.search(r"DATE[:\s]*(\d{4}-\d{2}-\d{2})", inv_part, re.I)
    invoice_date = m_date.group(1) if m_date else None
    if not invoice_date:
        m_date = re.search(r"DATE[:\s]*([A-Za-z]+\s+\d{1,2},\s*\d{4})", inv_part, re.I)
        invoice_date = en_date_to_iso(m_date.group(1)) if m_date else None

    amount = None
    m_amt = re.search(
        r"(?:TOTAL|Torau|Tota[lI])[^\n]{0,40}?([\d,]+\.\d{2})",
        inv_part,
        re.I,
    )
    if m_amt:
        amount = us_float(m_amt.group(1))

    incoterm = None
    m_inc = re.search(r"(FOB\s+SHANGHAI)", inv_part, re.I)
    if m_inc:
        incoterm = m_inc.group(1).upper()

    items: list[Item] = []
    seen: set[str] = set()
    for rx in (_LINE_WITH_DESC, _LINE):
        for m in rx.finditer(inv_part):
            pn = _fix_ocr_pn(m.group("pn"))
            key = pn + "|" + m.group("qty") + "|" + m.group("amt")
            if key in seen:
                continue
            seen.add(key)
            po = m.groupdict().get("po") or None
            if po and not po.upper().startswith("P"):
                po = "P" + po if po.isdigit() else po
            try:
                qty = us_float(m.group("qty"))
                price = us_float(m.group("price"))
                amt = us_float(m.group("amt"))
            except ValueError:
                continue
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=pn,
                    description="HEATING BELT",
                    qty=qty,
                    unit="PCS",
                    unit_price=price,
                    amount=amt,
                    origin="China",
                    currency="USD",
                )
            )

    # Prefer unique part numbers in order of first appearance
    # (second regex may duplicate)

    total_qty = sum(i.qty or 0 for i in items) or None
    if amount is None and items:
        amount = round(sum(i.amount or 0 for i in items), 2)

    # Packing list: try packages / GW
    total_pkg = None
    gw = None
    if "PACKING LIST" in text.upper() or "PACKING" in text.upper():
        m_pkg = re.search(r"(\d+)\s*(?:PALLET|PLT|plt)", text, re.I)
        if m_pkg:
            total_pkg = float(m_pkg.group(1))
        # OCR packing often has volume line "0.80" CBM and NW/GW columns — soft
        m_gw = re.search(r"([\d.]+)\s*KGS?", text, re.I)
        if m_gw:
            try:
                gw = us_float(m_gw.group(1))
            except ValueError:
                gw = None

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
        vendor="Shanghai Nature International Trading Co., Ltd.",
        origin="China",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="shanghai_nature_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="TOTAL",
    )
    if needs_ocr or not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
