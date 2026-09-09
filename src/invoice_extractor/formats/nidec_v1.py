"""NIDEC Techno Motor (JCH-TW) invoice v1.

Trained on JCH-TW_VKT25097 / VKT25098 layout text.
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
    "filename_regex": r"JCH|VKT\d+|NIDEC",
    "keywords": [
        "NIDEC TECHNO MOTOR",
        "Invoice No.",
        "Net Amount",
        "Johnson Controls-Hitachi",
    ],
}

NOTES = "NIDEC Techno Motor invoice for JCH-TW; seed from VKT25097/98"

RULES_JSON = {
    "id": "nidec_v1",
    "header": {
        "invoice_no": r"Invoice\s+No\.\s+(VKT\d+)",
        "amount": r"Net Amount\s+[\d,]+\s+pcs\s+USD\s+([\d,.]+)",
        "incoterm": r"Trade Terms\s*:\s*([^\n]+)",
        "pkg": r"Total\s+(\d+)\s+PALLETS?",
        "gw": r"Total\s+\d+\s+PALLETS?[^\n]*?([\d,.]+)\s+([\d,.]+)\s+([\d.]+)",
    },
}

_LINE = re.compile(
    r"(?P<n>\d+)\)\s+(?P<desc>\S+)\s+(?P<part>\S+)\s+"
    r"(?P<qty>[\d,]+)\s+PCS\s+(?P<price>[\d,.]+)\s+(?P<amt>[\d,.]+)",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "JCH" in fn or "VKT" in fn or "NIDEC" in fn:
        score += 0.35
    if "NIDEC TECHNO MOTOR" in text:
        score += 0.45
    if re.search(r"Invoice\s+No\.\s+VKT", text):
        score += 0.2
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    ci = text.split("PACKING LIST")[0]
    m_inv = re.search(r"Invoice\s+No\.\s+(VKT\d+)", text, re.I)
    invoice_no = m_inv.group(1) if m_inv else None

    m_date = re.search(r"Date\s+(\S[^\n]{0,30})", ci)
    invoice_date = None
    if m_date:
        invoice_date = en_date_to_iso(m_date.group(1).strip())

    m_net = re.search(
        r"Net Amount\s+([\d,]+)\s+pcs\s+USD\s+([\d,.]+)",
        ci,
        re.I,
    )
    net_qty = us_float(m_net.group(1)) if m_net else None
    amount = us_float(m_net.group(2)) if m_net else None

    m_terms = re.search(r"Trade Terms\s*:\s*([^\n]+)", ci, re.I)
    incoterm = m_terms.group(1).strip() if m_terms else None

    m_orig = re.search(r"Country of Origin\s*:\s*([A-Z]+)", text, re.I)
    origin = None
    if m_orig:
        o = m_orig.group(1).upper()
        origin = {"CHINA": "CN", "CN": "CN", "JAPAN": "JP"}.get(o, o[:2])

    # Packing list totals
    pl = text[text.find("PACKING LIST") :] if "PACKING LIST" in text else text
    m_pkg = re.search(r"Total\s+(\d+)\s+PALLETS?", pl, re.I)
    pkg = float(m_pkg.group(1)) if m_pkg else None
    m_gw = re.search(
        r"Total\s+\d+\s+PALLETS?\s+.*?([\d,.]+)\s+pcs\s+([\d,.]+)\s+([\d,.]+)",
        pl,
        re.I | re.S,
    )
    gw = us_float(m_gw.group(3)) if m_gw else None

    items: list[Item] = []
    for m in _LINE.finditer(ci):
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=m.group("part"),
                description=m.group("desc"),
                qty=us_float(m.group("qty")),
                unit="PCS",
                unit_price=us_float(m.group("price")),
                amount=us_float(m.group("amt")),
                origin=origin,
                currency="USD",
            )
        )

    if amount is None and items:
        amount = round(sum(it.amount or 0 for it in items), 2)
    total_qty = float(sum(it.qty or 0 for it in items)) if items else net_qty

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
        vendor="NIDEC TECHNO MOTOR CORPORATION",
        origin=origin,
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="nidec_v1",
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
