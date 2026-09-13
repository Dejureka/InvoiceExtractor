"""Qingdao Hisense Bosch Air-Conditioning — commercial invoice + packing list v1.

Combined PDF (COMMERCIAL INVOICE then PACKING LIST). Family keyed on
Qingdao Hisense Bosch layout (CI NO. CIHT-TW-…), not one-id-per-vendor.
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
    "filename_regex": r"CIHT-TW|HISENSE|INV\+PL\+CI",
    "keywords": [
        "QINGDAO HISENSE BOSCH",
        "COMMERCIAL INVOICE",
        "CI NO.",
        "SELLER'S MODEL",
        "BUYER'S MODEL",
    ],
}

NOTES = (
    "Qingdao Hisense Bosch Air-Conditioning combined INV+PL. "
    "PN = SELLER'S MODEL; amount label = invoice SETS/AMOUNT total row. "
    "Sample: INV+PL+CIHT-TW-26080473.pdf (case1)."
)

RULES_JSON = {
    "id": "hisense_qingdao_v1",
    "header": {
        "invoice_no": r"CI\s*NO\.?:\s*(CIHT-TW-\d+)",
        "amount": r"SETS/AMOUNT total row → last AMOUNT before form feed",
        "incoterm": r"TRADE TERM:\s*(\S+)",
        "pkg": r"PACKING LIST TOTAL … QTY.OF PKGS",
        "gw": r"PACKING LIST TOTAL … G.W. (KGS)",
        "currency": "USD",
    },
}

# Line: NO  BRAND  BUYER_MODEL  SELLER_MODEL  SETS  UNIT  AMOUNT  BUYER_NO
# Description column often empty in text layer.
_LINE = re.compile(
    r"^\s*(?P<no>\d+)\s+"
    r"(?P<brand>[A-Z][A-Z0-9 /&-]*)\s+"
    r"(?P<buyer>[A-Z0-9][A-Z0-9/-]*)\s+"
    r"(?P<seller>[A-Z0-9][A-Z0-9/-]*)\s+"
    r"(?P<qty>\d+)\s+"
    r"(?P<price>[\d,.]+)\s+"
    r"(?P<amt>[\d,.]+)\s+"
    r"(?P<po>P\d+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)

_TOTAL_QTY_AMT = re.compile(
    r"^\s*(?P<qty>\d+)\s+(?P<amt>[\d,.]+)\s*$",
    re.MULTILINE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "CIHT-TW" in fn or "HISENSE" in fn or "INV+PL+CI" in fn:
        score += 0.35
    if "QINGDAO HISENSE BOSCH" in text:
        score += 0.45
    if re.search(r"CI\s*NO\.?:\s*CIHT-TW-", text, re.I):
        score += 0.2
    if "COMMERCIAL INVOICE" in text and "PACKING LIST" in text:
        score += 0.1
    if "BITZER" in text or "MY-HUB FINANCE" in text or "AICHI ELECTRIC" in text:
        score -= 0.5
    if "GLOBAL LIFE SOLUTIONS" in text:
        score -= 0.4
    return max(0.0, min(score, 1.0))


def _invoice_chunk(text: str) -> str:
    m = re.search(r"\n\s*PACKING LIST\b", text, re.I)
    return text[: m.start()] if m else text


def _packing_chunk(text: str) -> str:
    m = re.search(r"\n\s*PACKING LIST\b", text, re.I)
    return text[m.start() :] if m else ""


def _parse_items(chunk: str, invoice_no: str | None, currency: str) -> list[Item]:
    items: list[Item] = []
    for m in _LINE.finditer(chunk):
        seller = m.group("seller").strip()
        buyer = m.group("buyer").strip()
        brand = m.group("brand").strip()
        desc = f"{brand} {buyer}".strip()
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=seller,
                description=desc or None,
                qty=us_float(m.group("qty")),
                unit="SETS",
                unit_price=us_float(m.group("price")),
                amount=us_float(m.group("amt")),
                origin="China",
                hs_code=None,
                currency=currency,
            )
        )
    return items


def _pkg_gw(packing: str) -> tuple[float | None, float | None]:
    # TOTAL  209  0  169  169  45986.00  43101.00  294.52
    m = re.search(
        r"(?im)^\s*TOTAL\s+[\d.,]+\s+[\d.,]+\s+(\d+)\s+\1\s+([\d.,]+)\s+[\d.,]+\s+[\d.,]+\s*$",
        packing,
    )
    if m:
        return float(m.group(1)), us_float(m.group(2))
    return None, None


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    inv_chunk = _invoice_chunk(text)
    pack_chunk = _packing_chunk(text)

    m_inv = re.search(r"CI\s*NO\.?:\s*(CIHT-TW-\d+)", text, re.I)
    invoice_no = m_inv.group(1) if m_inv else None

    m_date = re.search(r"CI\s*DATE:\s*(\d{4}-\d{2}-\d{2})", text, re.I)
    invoice_date = en_date_to_iso(m_date.group(1)) if m_date else None

    m_term = re.search(r"TRADE TERM:[ \t]*([A-Z]{3})(?:[ \t]+([A-Za-z]+))?", text, re.I)
    if m_term:
        incoterm = m_term.group(1).upper()
        if m_term.group(2):
            incoterm = f"{incoterm} {m_term.group(2)}"
    else:
        incoterm = None

    currency = "USD"
    if re.search(r"UNIT PRICE\s+AMOUNT[^\n]*\n[^\n]*USD", inv_chunk, re.I):
        currency = "USD"

    items = _parse_items(inv_chunk, invoice_no, currency)

    # Trailing qty/amount total on invoice (e.g. "209  361115")
    amount = None
    total_qty = None
    # Prefer last standalone qty+amount after last line item
    last_pos = 0
    for m in _LINE.finditer(inv_chunk):
        last_pos = m.end()
    tail = inv_chunk[last_pos:]
    m_tot = _TOTAL_QTY_AMT.search(tail)
    if m_tot:
        total_qty = us_float(m_tot.group("qty"))
        amount = us_float(m_tot.group("amt"))
    if amount is None and items:
        amount = round(sum(it.amount or 0.0 for it in items), 2)
    if total_qty is None and items:
        total_qty = sum(it.qty or 0.0 for it in items)

    pkg, gw = _pkg_gw(pack_chunk)

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
        vendor="QINGDAO HISENSE BOSCH AIR-CONDITIONING SYSTEM CO.,LTD.",
        origin="China",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="hisense_qingdao_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="INVOICE TOTAL AMOUNT",
        source="combined",
        notes="combined INV+PL; soft-missing HS OK",
    )
    if needs_ocr or not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
