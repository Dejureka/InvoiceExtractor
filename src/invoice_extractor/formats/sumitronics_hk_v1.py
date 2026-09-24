"""Sumitronics Hong Kong — PCBA commercial invoice + packing list v1.

BHC 3rd case3: ``ST0826170 INV&PL.pdf`` (+ xlsx twin).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, us_float

MATCH_HINTS = {
    "filename_regex": r"ST\d{7}|SUMITRONICS|INV&PL",
    "keywords": [
        "SUMITRONICS",
        "PCB ASSEMBLY",
        "FOB HAIPHONG",
        "PACKING LIST NO",
    ],
}

NOTES = (
    "Sumitronics HK combined INV+PL (ST########). PN = item code (1FA/2FA…). "
    "Sample: ST0826170 INV&PL.pdf / .xlsx (BHC 3rd case3)."
)

RULES_JSON = {
    "id": "sumitronics_hk_v1",
    "header": {
        "invoice_no": r"INVOICE NUMBER\s*:?\s*(ST\d+)",
        "amount": r"TOTAL\s*:?\s*[\d,.]+\s+([\d,]+\.\d{2})",
        "incoterm": r"(FOB\s+HAIPHONG)",
        "pkg": r"TOTAL:?\s*(\d+)\s*PLTS",
        "gw": r"TOTAL:?\s*\d+\s*PLTS[^\n]*?([\d,]+\.\d{2})",
    },
}

_LINE = re.compile(
    r"(?P<pn>[12]FA\w+)\s+(?P<desc>(?:IPM|POWER)\s+PCB\s+ASSEMBLY)\s+"
    r"(?P<qty>[\d,]+\.\d{2}|\d[\d,]*)\s+(?P<price>[\d.]+)\s+(?P<amt>[\d,]+\.\d{2})",
    re.IGNORECASE,
)
_LINE_XLS = re.compile(
    r"(?P<pn>[12]FA\w+)\t(?P<desc>(?:IPM|POWER)\s+PCB\s+ASSEMBLY)\t"
    r"(?P<qty>[\d.]+)\t(?P<price>[\d.]+)\t(?P<amt>[\d.]+)",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if "SUMITRONICS" in fn or re.search(r"ST\d{7}", fn):
        score += 0.3
    if "SUMITRONICS" in tu:
        score += 0.5
    if "FOB HAIPHONG" in tu:
        score += 0.15
    if "PCB ASSEMBLY" in tu:
        score += 0.1
    if "NIDEC" in tu or "BITZER" in tu or "AICHI ELECTRIC" in tu:
        score -= 0.5
    if "MY-HUB FINANCE" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    work = text
    if "=== Sheet:" in text:
        for part in re.split(r"=== Sheet:", text):
            title = part.split("===", 1)[0].strip().upper()
            if title.startswith("INV") or "INVOICE" in part[:200].upper():
                if "SUMITRONICS" in part.upper() or "ST0" in part:
                    work = part
                    break
    inv_part = re.split(r"PACKING\s+LIST", work, maxsplit=1, flags=re.I)[0]

    m_inv = re.search(r"INVOICE NUMBER\s*:?\s*(ST\d+)", inv_part, re.I)
    if not m_inv:
        m_inv = re.search(r"PACKING LIST NO\s*:?\s*(ST\d+)", text, re.I)
    if not m_inv:
        m_inv = re.search(r"\b(ST\d{7})\b", text)
    invoice_no = m_inv.group(1).upper() if m_inv else None

    m_date = re.search(r"DATE\s*:?\s*\n?\s*(\d{1,2}/\d{2}/\d{4})", inv_part, re.I)
    if not m_date:
        m_date = re.search(r"(\d{1,2}/[A-Za-z]{3}/\d{4})", text)
    invoice_date = m_date.group(1) if m_date else None

    amount = None
    total_qty = None
    m_tot = re.search(
        r"TOTAL\s*:?\s*([\d,]+\.\d{2})\s+([\d,]+\.\d{2})",
        inv_part,
        re.I,
    )
    if m_tot:
        total_qty = us_float(m_tot.group(1))
        amount = us_float(m_tot.group(2))
    if amount is None:
        m_tot = re.search(r"TOTAL\s*:?\t([\d.]+)\t([\d.]+)", inv_part, re.I)
        if m_tot:
            total_qty = us_float(m_tot.group(1))
            amount = us_float(m_tot.group(2))

    m_inc = re.search(r"(FOB\s+HAIPHONG)", inv_part, re.I)
    incoterm = m_inc.group(1).upper() if m_inc else None

    items: list[Item] = []
    for rx in (_LINE, _LINE_XLS):
        for m in rx.finditer(inv_part):
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=m.group("pn").upper(),
                    description=re.sub(r"\s+", " ", m.group("desc")).strip().title(),
                    qty=us_float(m.group("qty")),
                    unit="SETS",
                    unit_price=us_float(m.group("price")),
                    amount=us_float(m.group("amt")),
                    origin="VN",
                    currency="USD",
                )
            )
        if items:
            break

    # Packing totals: TOTAL: 36PLTS(563CTNS)        3,967         4,954.102667      6,937.40
    pkg = None
    gw = None
    m_pk = re.search(
        r"TOTAL:?\s*(\d+)\s*PLTS(?:\([^)]*\))?\s+([\d,]+)\s+[\d,.]+\s+([\d,]+\.\d{2})",
        text,
        re.I,
    )
    if m_pk:
        pkg = float(m_pk.group(1))
        if total_qty is None:
            total_qty = us_float(m_pk.group(2))
        gw = us_float(m_pk.group(3))

    if amount is None and items:
        amount = round(sum(it.amount or 0 for it in items), 2)
    if total_qty is None and items:
        total_qty = float(sum(it.qty or 0 for it in items))

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
        vendor="Sumitronics Hong Kong Ltd.",
        origin="VN",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="sumitronics_hk_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="TOTAL",
        source="combined",
    )
    if not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
