"""Suzhou Aichi Technology (苏州爱知) — combined INV+PKL v1 (OCR-friendly).

BHC 3rd case1: ``SATJG26010.pdf`` (scan). Distinct from Japan ``aichi_electric_v1`` (AETW).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, us_float

MATCH_HINTS = {
    "filename_regex": r"SATJG|SUZHOU.?AICHI|苏州爱知",
    "keywords": [
        "SUZHOU AICHI TECHNOLOGY",
        "SATJG",
        "ROTOR",
        "FOB SHENZHEN",
    ],
}

NOTES = (
    "Suzhou Aichi Technology combined INV+PKL (SATJG…). OCR OK on BHC 3rd case1. "
    "Not Japan Aichi Electric (AETW). Amount = sum(lines) when TOTAL OCR noisy."
)

RULES_JSON = {
    "id": "suzhou_aichi_v1",
    "header": {
        "invoice_no": r"INVOICE\s+NO\.?\s*(SATJG\w+)",
        "amount": r"USD\s*([\d,]+\.\d{2})",
        "incoterm": r"(FOB\s+SHENZHEN)",
        "pkg": r"(\d+)\s*(?:Plywood\s+)?Pallets",
        "gw": r"([\d,]+)\s*k[ge]s",
    },
}

# OCR-tolerant line: HS + ROTOR + PN + qty + USD price + USD amt
_LINE = re.compile(
    r"(?P<hs>\d{8,10})\s+ROTOR[^\n]{0,60}?"
    r"(?P<pn>TW\d+\s*\([^)]+\)|[A-Z0-9]{5,}\([^)]+\))\s+"
    r"(?P<qty>[\d,]+)\s*p[ec]s\s+USD\s*(?P<price>[\d., ]+?)\s+"
    r"USD\s*(?P<amt>[\d., ]+?)(?=\s*$|\s{2,}|\n|TOTAL|debate|E\.|&)",
    re.IGNORECASE | re.MULTILINE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if "SATJG" in fn or "SUZHOU" in fn and "AICHI" in fn:
        score += 0.35
    if "SUZHOU AICHI TECHNOLOGY" in tu or "SUZHOU AICHI" in tu:
        score += 0.5
    if re.search(r"\bSATJG\w+", tu):
        score += 0.2
    if "AICHI ELECTRIC" in tu and "SUZHOU" not in tu:
        score -= 0.6
    if "AETW" in tu:
        score -= 0.5
    if "NIDEC" in tu or "BITZER" in tu or "MARUBENI" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _clean_money(s: str) -> float | None:
    s = (s or "").strip()
    s = re.sub(r"\s+", "", s)
    s = s.replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return us_float(s)


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    m_inv = re.search(r"INVOICE\s+NO\.?\s*:?\s*(SATJG\w+)", text, re.I)
    if not m_inv:
        m_inv = re.search(r"\b(SATJG\w+)\b", text, re.I)
    invoice_no = m_inv.group(1).upper() if m_inv else None

    m_date = re.search(
        r"(?:DATE|日\s*期)\s*:?\s*(\d{1,2}/[A-Za-z]{3}/\d{2,4})",
        text,
        re.I,
    )
    invoice_date = None
    if m_date:
        # leave raw-ish; schema may not parse dd/Mon/yy — soft OK
        invoice_date = m_date.group(1)

    m_inc = re.search(r"(FOB\s+SHENZHEN)", text, re.I)
    incoterm = m_inc.group(1).upper() if m_inc else "FOB SHENZHEN"

    items: list[Item] = []
    for m in _LINE.finditer(text):
        price = _clean_money(m.group("price"))
        amt = _clean_money(m.group("amt"))
        qty = us_float(m.group("qty"))
        pn = re.sub(r"\s+", "", m.group("pn"))
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=pn,
                description="ROTOR",
                qty=qty,
                unit="PCS",
                unit_price=price,
                amount=amt,
                hs_code=m.group("hs"),
                origin="CN",
                currency="USD",
            )
        )

    # Fallback looser lines if OCR broke HS/PN glue
    if not items:
        loose = re.compile(
            r"ROTOR[^\n]{0,60}?(?P<qty>[\d,]+)\s*p[ec]s\s+USD\s*(?P<price>[\d,. ]+)\s+USD\s*(?P<amt>[\d,. ]+)",
            re.I,
        )
        for i, m in enumerate(loose.finditer(text), 1):
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=f"ROTOR-{i}",
                    description="ROTOR",
                    qty=us_float(m.group("qty")),
                    unit="PCS",
                    unit_price=_clean_money(m.group("price")),
                    amount=_clean_money(m.group("amt")),
                    origin="CN",
                    currency="USD",
                )
            )

    amount = None
    # Prefer sum of lines — OCR TOTAL often garbled
    if items and all(it.amount is not None for it in items):
        amount = round(sum(it.amount or 0 for it in items), 2)

    # Packing
    pkg = None
    gw = None
    # OCR packing rows: "No. 1-3 3 ROTOR …" / "No. 4-7 4 ROTOR …" → sum counts
    pallet_rows = re.findall(
        r"No[.,]\s*\d+\s*-\s*\d+\s+(\d+)\s+(?:\S+\s+)?ROTOR",
        text,
        re.I,
    )
    if not pallet_rows:
        pallet_rows = re.findall(r"No[.,]\s*\d+-\d+\s+(\d+)\s+ROTOR", text, re.I)
    if pallet_rows:
        pkg = float(sum(int(x) for x in pallet_rows))
    if pkg is None:
        m_plts = re.search(r"(\d+)\s*PLTS", text, re.I)
        if m_plts:
            pkg = float(m_plts.group(1))
    if pkg is None:
        m_ply = re.search(r"(\d+)\s*Plywood\s+Pallets", text, re.I)
        if m_ply:
            pkg = float(m_ply.group(1))
    # Gross from packing TOTAL line: … 3,876 kgs 4,121 kes
    m_gw = re.search(
        r"([\d,]+)\s*k[ge]s\s+([\d,]+)\s*k[ge]s\s+[\d,.]+\s*M",
        text,
        re.I,
    )
    if m_gw:
        gw = us_float(m_gw.group(2))
    if gw is None:
        # Arrival notice twin often 4,121.00 KGS — also on packing No. totals
        weights = re.findall(r"([\d,]+)\s*k[ge]s", text, re.I)
        # pick largest plausible GW
        vals = [us_float(w) for w in weights]
        vals = [v for v in vals if v and 1000 < v < 20000]
        if vals:
            gw = max(vals)

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=pkg,
        gross_weight_kg=gw,
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=float(sum(it.qty or 0 for it in items)) if items else None,
        amount=amount,
        currency="USD",
        vendor="SUZHOU AICHI TECHNOLOGY CO., LTD.",
        origin="CN",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="suzhou_aichi_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="sum(lines)",
        source="combined",
    )
    if not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
        meta.notes = "OCR partial — verify amount/PN vs figure"
    elif needs_ocr:
        meta.notes = "OCR backend — Auditor should confirm figure vs JSON"
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
