"""Dongguan Ohizumi Sensor (东莞大泉) — temperature sensor INV+PL v1.

BHC 3rd case6: ``(發票)…东莞大泉.pdf`` + PL + .xls twin.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, us_float

MATCH_HINTS = {
    "filename_regex": r"OHIZUMI|东莞大泉|26575",
    "keywords": [
        "DONG GUAN OHIZUMI",
        "OHIZUMI",
        "TEMPERATURE SENSOR",
        "东莞大泉",
    ],
}

NOTES = (
    "Dongguan Ohizumi Sensor (东莞大泉) INV+PL. Invoice OHIZUMI-#####OUT. "
    "Excel .xls supported via excel/xlrd. Sample: 26-09-14.26575A (BHC 3rd case6)."
)

RULES_JSON = {
    "id": "ohizumi_dongguan_v1",
    "header": {
        "invoice_no": r"INVOICE\s+NO\.?\s*:?\s*(OHIZUMI[-\w]+)",
        "amount": r"TOTAL\s+[\d,]+\s+PCS\s+USD\s*([\d,]+\.?\d*)",
        "pkg": r"TWENTY-TWO\s*\(22\)\s*CARTONS|TOTAL\s+(\d+)\s+CARTONS",
        "gw": r"TOTAL\s+\d+\s+[\d,]+\s+PCS\s+[\d.]+\s+([\d.]+)\s+KGS",
    },
}

# PDF layout: 3FM81374A   100-054-00274   1000     PCS USD         1.8621    USD     1,862.10
_LINE_PDF = re.compile(
    r"(?P<pn>3FM\w+)\s+(?P<vpn>\d{3}-\d{3}-\d{5})\s+"
    r"(?P<qty>[\d,]+)\s+PCS\s+USD\s*(?P<price>[\d.]+)\s+USD\s*(?P<amt>[\d,]+\.?\d*)",
    re.IGNORECASE,
)
# Excel tab-joined: 3FM81374A\t100-054-00274\t1000\tPCS\tUSD\t1.8621\tUSD\t1862.10
_LINE_XLS = re.compile(
    r"(?P<pn>3FM\w+)\t(?P<vpn>\d{3}-\d{3}-\d{5})\t"
    r"(?P<qty>[\d.]+)\tPCS\tUSD\t(?P<price>[\d.]+)\tUSD\t(?P<amt>[\d.]+)",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if "OHIZUMI" in fn or "东莞大泉" in filename or "26575" in fn:
        score += 0.3
    if "DONG GUAN OHIZUMI" in tu or "OHIZUMI SENSOR" in tu or "东莞大泉" in text:
        score += 0.5
    if "TEMPERATURE" in tu and "SENSOR" in tu:
        score += 0.1
    if "SUMITRONICS" in tu or "DUNAN" in tu or "NIDEC TECHNO" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    m_inv = re.search(r"INVOICE\s+NO\.?\s*:?\s*(OHIZUMI[-\w]+)", text, re.I)
    invoice_no = m_inv.group(1).upper() if m_inv else None

    m_date = re.search(r"DATE:?\s*([\d/\-]+(?:\s+\d+:\d+:\d+)?)", text, re.I)
    invoice_date = m_date.group(1).strip()[:10] if m_date else None

    amount = None
    total_qty = None
    m_tot = re.search(
        r"TOTAL\s+([\d,]+)\s+PCS\s+USD\s*([\d,]+\.?\d*)",
        text,
        re.I,
    )
    if m_tot:
        total_qty = us_float(m_tot.group(1))
        amount = us_float(m_tot.group(2))

    items: list[Item] = []
    for rx in (_LINE_PDF, _LINE_XLS):
        for m in rx.finditer(text):
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=m.group("pn").upper(),
                    description="TEMPERATURE SENSOR",
                    qty=us_float(m.group("qty")),
                    unit="PCS",
                    unit_price=us_float(m.group("price")),
                    amount=us_float(m.group("amt")),
                    origin="CN",
                    currency="USD",
                )
            )
        if items:
            break

    pkg = None
    gw = None
    if re.search(r"TWENTY-TWO\s*\(22\)\s*CARTONS", text, re.I):
        pkg = 22.0
    m_pk = re.search(r"TOTAL\s+(\d+)\s+([\d,]+)\s+PCS\s+([\d.]+)\s+([\d.]+)\s+KGS", text, re.I)
    if m_pk:
        pkg = float(m_pk.group(1))
        gw = us_float(m_pk.group(4))
    # Excel packing TOTAL row: TOTAL\t22\t4300\tPCS\t250.26\t267.86\tKGS
    m_x = re.search(r"TOTAL\t(\d+)\t([\d.]+)\tPCS\t([\d.]+)\t([\d.]+)\tKGS", text, re.I)
    if m_x:
        pkg = float(m_x.group(1))
        gw = us_float(m_x.group(4))

    if amount is None and items:
        amount = round(sum(it.amount or 0 for it in items), 2)
    if total_qty is None and items:
        total_qty = float(sum(it.qty or 0 for it in items))

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=pkg,
        gross_weight_kg=gw,
        incoterm=None,
        item_line_count=len(items) if items else None,
        total_quantity=total_qty,
        amount=amount,
        currency="USD",
        vendor="DONG GUAN OHIZUMI SENSOR CO.,LTD.",
        origin="CN",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="ohizumi_dongguan_v1",
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
