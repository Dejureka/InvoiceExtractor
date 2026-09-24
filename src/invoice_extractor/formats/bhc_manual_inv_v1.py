"""BHC MY-HUB TW-MANUAL invoice (damage / no commercial value) v1.

BHC 3rd case4: ``INV#TW-MANUAL-015-BHCWHQA260915A.pdf``. Same vendor as
``bhc_my_hub_v1`` but different layout (no TOTALS: / PART NO table).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, us_float

MATCH_HINTS = {
    "filename_regex": r"TW-MANUAL|BHCWHQA",
    "keywords": [
        "TW-MANUAL",
        "no commercial value",
        "INVOICE No:TW-MANUAL",
    ],
}

NOTES = (
    "BHC Supply (M) TW-MANUAL invoices (damage replacement). Soft-missing "
    "pkg/GW OK; pair PKL when present. Sample: INV#TW-MANUAL-015-BHCWHQA260915A."
)

RULES_JSON = {
    "id": "bhc_manual_inv_v1",
    "header": {
        "invoice_no": r"INVOICE\s*No:?\s*(TW-MANUAL-\d+)",
        "amount": r"TOTAL\s+\$?\s*([\d,]+\.\d{2})",
    },
}

_LINE = re.compile(
    r"^\s*(?P<n>\d+)\s+(?P<pn>A\d+\w*)\s+\1?\s*(?P=pn)?\s+(?P<desc>[A-Z. ]+?)\s+"
    r"(?P<qty>\d+)\s+\$?\s*(?P<price>[\d.]+)\s+\$?\s*(?P<amt>[\d,]+\.\d{2})",
    re.MULTILINE | re.IGNORECASE,
)
_LINE2 = re.compile(
    r"(?P<n>\d+)\s+(?P<pn>A\d+\w*)\s+(?P=pn)\s+(?P<desc>PCB\s+AS\.?)\s+"
    r"(?P<qty>\d+)\s+\$\s*(?P<price>[\d.]+)\s+\$\s*(?P<amt>[\d,]+\.\d{2})",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if "TW-MANUAL" in fn or "BHCWHQA" in fn:
        score += 0.35
    if "TW-MANUAL" in tu:
        score += 0.5
    if "no commercial value" in text.lower():
        score += 0.15
    if "TOTALS:" in text and "PART NO" in text:
        score -= 0.5  # real MY-HUB table
    if "MY-HUB FINANCE" in tu:
        score -= 0.3
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    m_inv = re.search(r"INVOICE\s*No:?\s*(TW-MANUAL-\d+)", text, re.I)
    invoice_no = m_inv.group(1).upper() if m_inv else None

    m_date = re.search(r"Date\s+(\d{1,2}-[A-Za-z]{3}-\d{2})", text, re.I)
    invoice_date = m_date.group(1) if m_date else None

    amount = None
    m_amt = re.search(r"TOTAL\s+\$?\s*([\d,]+\.\d{2})", text, re.I)
    if m_amt:
        amount = us_float(m_amt.group(1))

    items: list[Item] = []
    for rx in (_LINE2, _LINE):
        for m in rx.finditer(text):
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=m.group("pn").upper(),
                    description=re.sub(r"\s+", " ", m.group("desc")).strip(),
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

    if amount is None and items:
        amount = round(sum(it.amount or 0 for it in items), 2)

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=None,
        gross_weight_kg=None,
        incoterm=None,
        item_line_count=len(items) if items else None,
        total_quantity=float(sum(it.qty or 0 for it in items)) if items else None,
        amount=amount,
        currency="USD",
        vendor="Bosch Home Comfort Supply (M) Sdn. Bhd.",
        origin="CN",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="bhc_manual_inv_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="TOTAL",
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
