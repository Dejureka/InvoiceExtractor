"""Changzhou Oukai Electric (常州欧凯) — stepper motor INV+PL v1 (Excel-first).

BHC 3rd case7: ``OK20260921.xls`` (+ scan BL). Legacy .xls via excel/xlrd.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, us_float

MATCH_HINTS = {
    "filename_regex": r"OK\d{8}|OUKAI|欧凯",
    "keywords": [
        "Changzhou Oukai",
        "OUKAI",
        "Step Motor",
        "欧凯",
        "OK20",
    ],
}

NOTES = (
    "Changzhou Oukai Electric stepper-motor INV+PL. Primary source often .xls "
    "(excel/xlrd). Sample: OK20260921.xls (BHC 3rd case7). "
    "Auditor 2026-09-24: vendor Total qty cell 10750 is a typo (omits 10000 line); "
    "line-sum qty 20750 is correct — hard_check uses sum(lines); soft note when "
    "labeled Total qty disagrees with sum(lines)."
)

RULES_JSON = {
    "id": "oukai_v1",
    "header": {
        "invoice_no": r"Invoice\s*No:?\s*(OK\d+)",
        "amount": r"Total\t[\d.]+\t([\d.]+)",
        "incoterm": r"(FOB\s+shanghai)",
        "pkg": r"Total\t[\d.]+\t(\d+)\t",
        "gw": r"Total\t[\d.]+\t\d+\t[\d.]+\t([\d.]+)",
    },
}

# Excel: Step Motor\n 3NA71563J ... then qty/price/amt on following cells joined
# Tab form after flattening: 3NA71563J ... 250 0.72 180
_LINE = re.compile(
    r"(?P<pn>3NA\w+)\s*(?:＜5W|DC)?\s*(?:DC)?\t?"
    r"(?P<qty>[\d.]+)\t(?P<price>[\d.]+)\t(?P<amt>[\d.]+)",
    re.IGNORECASE,
)
# Also tolerate space-joined from PDF OCR later
_LINE_SP = re.compile(
    r"(?P<pn>3NA\w+)\s+(?P<qty>[\d,]+)\s+(?P<price>[\d.]+)\s+(?P<amt>[\d,]+)",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if re.search(r"OK\d{8}", fn) or "OUKAI" in fn or "欧凯" in filename:
        score += 0.35
    if "CHANGZHOU OUKAI" in tu or "OUKAI ELECTRIC" in tu or "常州欧凯" in text:
        score += 0.5
    if "STEP MOTOR" in tu:
        score += 0.1
    if "NIDEC TECHNO" in tu or "OHIZUMI" in tu or "DUNAN" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    m_inv = re.search(r"Invoice\s*No:?\s*(OK\d+)", text, re.I)
    invoice_no = m_inv.group(1).upper() if m_inv else None

    m_date = re.search(r"Date:?\s*(Sep\.?\s*\d{1,2}\w*,?\s*\d{4})", text, re.I)
    invoice_date = m_date.group(1) if m_date else None

    amount = None
    total_qty = None
    # Excel INV total: Total\t10750\t14755
    m_tot = re.search(r"Total\t([\d.]+)\t([\d.]+)\s*$", text, re.I | re.M)
    if m_tot:
        total_qty = us_float(m_tot.group(1))
        amount = us_float(m_tot.group(2))
    if amount is None:
        m_tot2 = re.search(r"Total\s+([\d,]+)\s+([\d,]+)\s*$", text, re.I | re.M)
        if m_tot2:
            total_qty = us_float(m_tot2.group(1))
            amount = us_float(m_tot2.group(2))

    m_inc = re.search(r"(FOB\s+shanghai)", text, re.I)
    incoterm = "FOB SHANGHAI" if m_inc else None

    items: list[Item] = []
    # Prefer sheet 发票 / COMMERCIAL INVOICE block; never scan 箱单 packing
    inv_chunk = text
    if "=== Sheet:" in text:
        parts = re.split(r"=== Sheet:", text)
        for part in parts:
            head = part[:80]
            if "箱单" in head or "PACKING" in head.upper():
                continue
            if "发票" in head or "COMMERCIAL INVOICE" in part.upper() or "INVOICE" in head.upper():
                inv_chunk = part
                break
    # Drop packing list half if present in same sheet
    inv_chunk = re.split(r"PACKING\s+LIST", inv_chunk, maxsplit=1, flags=re.I)[0]

    seen: set[str] = set()
    for rx in (_LINE, _LINE_SP):
        for m in rx.finditer(inv_chunk):
            pn = m.group("pn").upper()
            qty = us_float(m.group("qty"))
            price = us_float(m.group("price"))
            amt = us_float(m.group("amt"))
            # Skip packing-list false hits (CTNS/NW/GW columns): amt should ≈ qty*price
            if qty and price and amt is not None:
                if abs((qty * price) - amt) > max(1.0, 0.05 * abs(amt)):
                    continue
            if pn in seen:
                continue
            seen.add(pn)
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=pn,
                    description="Step Motor",
                    qty=qty,
                    unit="PCS",
                    unit_price=price,
                    amount=amt,
                    origin="CN",
                    currency="USD",
                )
            )
        if items:
            break

    # Packing sheet totals: Total\t10750\t83\t747\t830\t2.905
    pkg = None
    gw = None
    m_pk = re.search(
        r"Total\t([\d.]+)\t(\d+)\t([\d.]+)\t([\d.]+)\t([\d.]+)",
        text,
        re.I,
    )
    if m_pk:
        pkg = float(m_pk.group(2))
        gw = us_float(m_pk.group(4))

    if amount is None and items:
        amount = round(sum(it.amount or 0 for it in items), 2)
    sum_qty = float(sum(it.qty or 0 for it in items)) if items else None
    qty_note = None
    # Source Total row sometimes under-states qty vs lines (OK20260921: 10750 vs 20750);
    # trust sum(lines) when both present and disagree (vendor typo — Auditor confirmed).
    if sum_qty is not None:
        if total_qty is not None and abs(total_qty - sum_qty) > 0.5:
            qty_note = (
                f"vendor Total qty {total_qty:g} != sum(lines) {sum_qty:g}; "
                "using sum(lines)"
            )
            total_qty = sum_qty
        elif total_qty is None:
            total_qty = sum_qty

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
        vendor="Changzhou Oukai Electric Co.,Ltd",
        origin="CN",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="oukai_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="Total",
        source="combined",
        notes=qty_note,
    )
    if not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
