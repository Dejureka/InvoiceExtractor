"""Hitachi Asia Ltd. / HITT induction motor — commercial invoice v1.

BHC 3rd case8: ``USDI4105369.pdf`` (Hitachi Asia; HITT motor nos). Distinct from
``hitachi_gls_v1`` (MEH / Global Life Solutions JPY).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, us_float

MATCH_HINTS = {
    "filename_regex": r"USDI\d+|HITT|HITACHI.?ASIA",
    "keywords": [
        "Hitachi Asia Ltd",
        "HITACHI INDUCTION MOTOR",
        "USDI",
        "HITT NO",
        "BHC NO",
    ],
}

NOTES = (
    "Hitachi Asia Ltd commercial invoice (USDI…). PN = BHC NO (2NB…). "
    "Not hitachi_gls_v1 (MEH). Sample: USDI4105369 (BHC 3rd case8 HITT)."
)

RULES_JSON = {
    "id": "hitachi_asia_hitt_v1",
    "header": {
        "invoice_no": r"Invoice\s+No\.?\s*(USDI\d+)",
        "amount": r"GRAND\s+TOTAL\s+([\d,]+\.\d{2})",
        "incoterm": r"Delivery\s+Term\s+(CIF\s+\w+)",
    },
}

# Line block: 1  1.5KW EFOUP-K 4P  12 PIECE 105.0500  1,260.60 + BHC NO: 2NB06322A
_LINE_AMT = re.compile(
    r"^\s*(?P<n>\d+)\s+(?P<desc>.+?)\s+"
    r"(?P<qty>[\d,]+)\s+PIECE\s+(?P<price>[\d.]+)\s+(?P<amt>[\d,]+\.\d{2})",
    re.MULTILINE | re.IGNORECASE,
)
_BHC = re.compile(r"BHC\s*NO:\s*(?P<pn>2[A-Z0-9]+)", re.I)
_HITT = re.compile(r"HITT\s*NO:\s*(?P<hitt>\S+)", re.I)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if "USDI" in fn or "HITT" in fn:
        score += 0.3
    if "HITACHI ASIA" in tu:
        score += 0.45
    if "HITACHI INDUCTION MOTOR" in tu or "HITT NO" in tu:
        score += 0.2
    if re.search(r"\bUSDI\d+", tu):
        score += 0.15
    if "GLOBAL LIFE SOLUTIONS" in tu or re.search(r"\bMEH\w+", tu):
        score -= 0.7
    if "NIDEC TECHNO" in tu or "MY-HUB FINANCE" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    m_inv = re.search(r"Invoice\s+No\.?\s*(USDI\d+)", text, re.I)
    if not m_inv:
        m_inv = re.search(r"\b(USDI\d+)\b", text, re.I)
    invoice_no = m_inv.group(1).upper() if m_inv else None

    m_date = re.search(r"Date of Issue\s+(\d{1,2}/\s*\d{1,2}/\s*\d{4})", text, re.I)
    invoice_date = re.sub(r"\s+", "", m_date.group(1)) if m_date else None

    amount = None
    m_amt = re.search(r"GRAND\s+TOTAL\s+([\d,]+\.\d{2})", text, re.I)
    if not m_amt:
        m_amt = re.search(r"TOTAL\s+([\d,]+\.\d{2})\s*\n\s*DISCOUNT", text, re.I)
    if m_amt:
        amount = us_float(m_amt.group(1))

    m_inc = re.search(r"Delivery\s+Term\s+(CIF\s+\w+)", text, re.I)
    incoterm = m_inc.group(1).upper() if m_inc else None

    items: list[Item] = []
    # Walk lines: pair each numbered amount row with following BHC NO
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = _LINE_AMT.match(lines[i])
        if m:
            # look ahead for BHC NO within next 6 lines
            pn = None
            desc = re.sub(r"\s+", " ", m.group("desc")).strip()
            for j in range(i + 1, min(i + 8, len(lines))):
                mb = _BHC.search(lines[j])
                if mb:
                    pn = mb.group("pn").upper()
                    break
                if _LINE_AMT.match(lines[j]):
                    break
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=pn or f"LINE{m.group('n')}",
                    description=desc,
                    qty=us_float(m.group("qty")),
                    unit="PIECE",
                    unit_price=us_float(m.group("price")),
                    amount=us_float(m.group("amt")),
                    origin="TH",
                    currency="USD",
                )
            )
        i += 1

    if amount is None and items:
        amount = round(sum(it.amount or 0 for it in items), 2)

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=None,  # soft — use BL / PKL overlay
        gross_weight_kg=None,
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=float(sum(it.qty or 0 for it in items)) if items else None,
        amount=amount,
        currency="USD",
        vendor="Hitachi Asia Ltd.",
        origin="TH",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="hitachi_asia_hitt_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="GRAND TOTAL",
        source="split",
    )
    if not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
