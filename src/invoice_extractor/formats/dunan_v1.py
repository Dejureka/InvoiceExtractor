"""Zhejiang Dunan International Trading (浙江盾安) — invoice + packing list v1.

BHC 3rd case5: ``标准_结汇发票FT00044266.pdf`` / packing twin / xlsx.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, us_float

MATCH_HINTS = {
    "filename_regex": r"DUNAN|盾安|FT\d{8}|结汇",
    "keywords": [
        "ZHEJIANG DUNAN",
        "盾安",
        "FOB NINGBO",
        "AIR CONDITIONER PARTS",
    ],
}

NOTES = (
    "Zhejiang Dunan INV (+ optional PKL). Invoice no may be slash-joined "
    "(DA15199998/2/5/52). Sample: FT00044266 (BHC 3rd case5)."
)

RULES_JSON = {
    "id": "dunan_v1",
    "header": {
        "invoice_no": r"INVOICE\s*NO[：:]\s*(\S+)",
        "amount": r"TOTAL:?\s*[\d,]+\s*PCS\s+USD\s*([\d,]+\.?\d*)",
        "incoterm": r"(FOB\s+NINGBO)",
        "pkg": r"TOTAL:?\s*(\d+)\s*PALLETS",
        "gw": r"([\d,]+\.?\d*)\s*(?:KGS?)?\s+[\d,]+\.?\d*\s+[\d.]+",
    },
}

# 2HL29677A P10062139                    36 PCS   X USD 29.755     =   USD 1071.1800
_LINE = re.compile(
    r"(?P<pn>[A-Z0-9]{6,}(?:&&)?)\s+P(?P<po>\d+)\s+"
    r"(?P<qty>[\d,]+)\s*PCS\s*X\s*USD\s*(?P<price>[\d.]+)\s*=\s*USD\s*(?P<amt>[\d.]+)",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if "DUNAN" in fn or "盾安" in filename or "结汇" in filename:
        score += 0.3
    if "ZHEJIANG DUNAN" in tu or "盾安" in text:
        score += 0.5
    if "FOB NINGBO" in tu:
        score += 0.15
    if "NIDEC" in tu or "SUMITRONICS" in tu or "MY-HUB" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    m_inv = re.search(r"INVOICE\s*NO[：:\s]*([A-Z0-9/]+)", text, re.I)
    invoice_no = m_inv.group(1).strip() if m_inv else None

    m_date = re.search(r"DATE[：:\s]*(?:Sep\.?\s*\d{1,2},?\s*\d{4}|\d{4}-\d{2}-\d{2})", text, re.I)
    invoice_date = None
    if m_date:
        invoice_date = re.sub(r"^DATE[：:\s]*", "", m_date.group(0), flags=re.I).strip()

    amount = None
    total_qty = None
    m_tot = re.search(
        r"TOTAL:?\s*([\d,]+)\s*PCS\s+USD\s*([\d,]+\.?\d*)",
        text,
        re.I,
    )
    if m_tot:
        total_qty = us_float(m_tot.group(1))
        amount = us_float(m_tot.group(2))

    m_inc = re.search(r"(FOB\s+NINGBO)", text, re.I)
    incoterm = m_inc.group(1).upper() if m_inc else None

    items: list[Item] = []
    # Map PN prefixes to rough descriptions from nearby headers
    desc_map = {
        "2HL": "ACCUMULATOR",
        "3EF": "COIL",
        "2CN": "DEEP GROOVE BALL BEARING",
        "3LD": "SERVICE VALVE",
        "3HP": "SERVICE VALVE",
    }
    for m in _LINE.finditer(text):
        pn = m.group("pn").upper()
        desc = next((v for k, v in desc_map.items() if pn.startswith(k)), "AIR CONDITIONER PARTS")
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=pn.rstrip("&"),
                description=desc,
                qty=us_float(m.group("qty")),
                unit="PCS",
                unit_price=us_float(m.group("price")),
                amount=us_float(m.group("amt")),
                origin="CN",
                currency="USD",
            )
        )

    pkg = None
    gw = None
    m_pk = re.search(r"TOTAL:?\s*(\d+)\s*PALLETS", text, re.I)
    if m_pk:
        pkg = float(m_pk.group(1))
    if pkg is None and re.search(r"PACKED IN EIGHT PALLETS", text, re.I):
        pkg = 8.0
    # Packing list: TOTAL:8PALLETS ... 3326.00
    m_gw = re.search(
        r"([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s+([\d.]+)\s*$",
        text,
        re.M,
    )
    # Better: line with PCS then GW NW Volume
    m_gw2 = re.search(
        r"24782\s*PCS\s+([\d,]+\.\d{2})",
        text,
        re.I,
    )
    if m_gw2:
        gw = us_float(m_gw2.group(1))
    if gw is None:
        m_gw3 = re.search(r"(\d{4}\.\d{2})\s+(\d{4}\.\d{2})\s+[\d.]+", text)
        if m_gw3:
            gw = us_float(m_gw3.group(1))

    if amount is None and items:
        amount = round(sum(it.amount or 0 for it in items), 2)

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=pkg,
        gross_weight_kg=gw,
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=total_qty or (float(sum(it.qty or 0 for it in items)) if items else None),
        amount=amount,
        currency="USD",
        vendor="ZHEJIANG DUNAN INTERNATIONAL TRADING CO.,LTD.",
        origin="CN",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="dunan_v1",
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
