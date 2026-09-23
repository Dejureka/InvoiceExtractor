"""Robert Bosch GmbH Mobility Aftermarket — Billing Document AK… invoices.

New family for ``Invoice AK########.PDF`` (MY ADC outbound). Distinct from
``ma_no_period_v1`` / ``ma_with_period_v1`` (Document No. 2000… / Goods Value).
HS = Commodity Code; Origin = Country of Origin on each line (no COO Index).
"""

from __future__ import annotations

import re

from invoice_extractor.formats.ma_common import parse_ak_packages
from invoice_extractor.schema import (
    ExtractResult,
    Header,
    Item,
    Meta,
    de_date_to_iso,
    us_float,
)

MATCH_HINTS = {
    "filename_regex": r"Invoice\s+AK\d{8}|AK\d{8}",
    "keywords": [
        "Billing Document",
        "Bosch Material No.",
        "Commodity Code",
        "Country of Origin",
        "Net value",
        "ADC MY outbound",
    ],
}

NOTES = (
    "MA Billing Document AK######## (Invoice AK….PDF / AK…_INV.PDF). "
    "PN like 0263.063.737-F0U / H105.025.303-Y8K; HS=Commodity Code; "
    "Origin=Country of Origin per line (not COO Index). "
    "Packages/GW from Marking HU / Dummy Pack. Mat. (not line Gross Weight). "
    "Net Value may differ slightly from Unit Price×Qty (commercial conditions); "
    "trust printed Net Value; hard_check allows 0.1% relative line tol. "
    "Samples: MAnewSample 40-D / 50-N / 90-S; MA-747 90-S-26MA-747 FWD+SAP."
)

RULES_JSON = {
    "id": "ma_ak_billing_v1",
    "header": {
        "invoice_no": r"Billing Document\s+(AK\d{8,})",
        "amount": r"Net value\s+([\d,]+)\s*TWD",
        "incoterm": r"Incoterms\s+([^\n]+)",
        "currency": r"Net value\s+[\d,]+\s*(TWD|USD|EUR)",
    },
    "items": {
        "line": (
            r"(\d{1,3})\s+([A-Z0-9]+(?:\.[A-Z0-9]+)+-[A-Z0-9]+)\s+"
            r"([\d,]+)\s+PC\s+([\d,]+)\s+([\d,]+)"
        ),
    },
}

# Item header row: pos + dotted/hyphen PN + qty PC + unit price + net value
_ITEM = re.compile(
    r"^(?P<pos>\d{1,3})\s+(?P<pn>[A-Z0-9]+(?:\.[A-Z0-9]+)+(?:-[A-Z0-9]+)?)\s+"
    r"(?P<qty>[\d,]+(?:\.\d+)?)\s+(?P<uom>PC|EA|SET|SA|PCE)\s+"
    r"(?P<price>[\d,]+(?:\.\d+)?)(?:\s+(?P<amt>[\d,]+(?:\.\d+)?))?"
    r"(?:\s+[\d,]+%\s+[\d,]+)?\s*$",
    re.MULTILINE,
)
_NEXT_ITEM = re.compile(
    r"^\d{1,3}\s+[A-Z0-9]+(?:\.[A-Z0-9]+)+(?:-[A-Z0-9]+)?\s+[\d,]+(?:\.\d+)?\s+(?:PC|EA|SET|SA|PCE)\b"
)
_HS = re.compile(r"Commodity\s+Cod(?:e|e)\s+(\d{6,12})", re.I)
_COO = re.compile(r"Country of Origin\s+([A-Z]{2})\b", re.I)
_PAGE_NOISE = re.compile(
    r"Bank Details|Registered Office|Managing Directors|Bosch Contacts|"
    r"Robert Bosch GmbH|Bill to Party|Billing Document|Item\s+Bosch Material|"
    r"The document is valid|Chairman/",
    re.I,
)
_DESC = re.compile(r"^\s{2,}([A-Za-z][A-Za-z0-9 /&\-.,]{2,80}?)\s{2,}|\s{2,}([A-Za-z][A-Za-z0-9 /&\-.,]{2,80})\s*$")


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    # AK########_INV (FWD) has no word-boundary after digits; also Invoice AK…
    if re.search(r"AK\d{8}", fn):
        score += 0.35
    if re.search(r"Billing Document\s+AK\d+", text):
        score += 0.35
    if "Bosch Material No." in text or "Commodity Code" in text:
        score += 0.2
    if "ADC MY outbound" in text or "Country of Origin" in text:
        score += 0.15
    # Not the Document-No / Goods-Value MA family
    if re.search(r"Document\s+No\.:?\s+\d{8,12}", text) and "Billing Document" not in text:
        score -= 0.5
    if re.search(r"Goods\s+[Vv]alue", text) and "Billing Document" not in text:
        score -= 0.4
    if "Power Tools GmbH" in text or "Net invoiced value of goods" in text:
        score -= 0.5
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _invoice_no(text: str) -> str | None:
    m = re.search(r"Billing Document\s+(AK\d{8,})", text)
    return m.group(1) if m else None


def _invoice_date(text: str) -> str | None:
    m = re.search(r"Billing Date\s+(\d{2}\.\d{2}\.\d{4})", text)
    return de_date_to_iso(m.group(1)) if m else None


def _net_value(text: str) -> float | None:
    m = re.search(r"Net value\s+([\d,]+)\s*(TWD|USD|EUR)", text)
    if m:
        return us_float(m.group(1))
    m = re.search(r"Subtotal of net value based\s+([\d,]+)\s*(TWD|USD|EUR)", text)
    return us_float(m.group(1)) if m else None


def _currency(text: str) -> str | None:
    m = re.search(r"Net value\s+[\d,]+\s*(TWD|USD|EUR)", text)
    if m:
        return m.group(1)
    m = re.search(r"Subtotal of net value based\s+[\d,]+\s*(TWD|USD|EUR)", text)
    return m.group(1) if m else None


def _incoterm(text: str) -> str | None:
    m = re.search(r"Incoterms\s+([^\n]+)", text)
    if m:
        return re.sub(r"\s{2,}", " ", m.group(1)).strip() or None
    return None


def _parse_items(text: str, invoice_no: str | None, currency: str | None) -> list[Item]:
    items: list[Item] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _ITEM.match(line)
        if not m:
            continue
        pn = m.group("pn")
        qty = us_float(m.group("qty"))
        price = us_float(m.group("price"))
        amt_raw = m.groupdict().get("amt")
        amt = us_float(amt_raw) if amt_raw else round(qty * price, 2)
        desc = None
        hs = None
        origin = None
        # Scan following lines until next item
        for j in range(i + 1, min(i + 45, len(lines))):
            ln = lines[j]
            if _ITEM.match(ln) or _NEXT_ITEM.match(ln):
                break
            if "Marking" in ln and j > i + 3:
                break
            if _PAGE_NOISE.search(ln):
                continue  # keep scanning past page footer/header
            if desc is None:
                dm = re.match(
                    r"^\s{2,}(?!Customer|Commodity|Country|EAN|Net Weight|Gross Weight|Handling|Net Val|POS-no)"
                    r"([A-Za-z][A-Za-z0-9 /&\-.,'+]{2,90}?)\s*$",
                    ln,
                )
                if dm:
                    desc = dm.group(1).strip()
            hm = _HS.search(ln)
            if hm and hs is None:
                hs = hm.group(1)
            cm = _COO.search(ln)
            if cm and origin is None:
                origin = cm.group(1)
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=pn,
                description=(re.sub(r'\s+\d+\s*(PC|EA|SET)\s*$', '', re.sub(r'\s{2,}.*$', '', desc)).strip() if desc else None),
                qty=qty,
                unit=m.group("uom"),
                unit_price=price,
                amount=amt,
                origin=origin,
                hs_code=hs,
                currency=currency,
            )
        )
    return items


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    invoice_no = _invoice_no(text)
    invoice_date = _invoice_date(text)
    amount = _net_value(text)
    currency = _currency(text)
    incoterm = _incoterm(text)
    pkg, gw = parse_ak_packages(text)
    items = _parse_items(text, invoice_no, currency)
    total_qty = sum(it.qty or 0.0 for it in items) if items else None
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
        vendor="Robert Bosch GmbH (MA AK Billing)",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="ma_ak_billing_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="Net value",
    )
    if needs_ocr or not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    # HS required — flag if any line missing
    if items and any(not it.hs_code for it in items):
        meta.notes = (meta.notes or "") + " missing_line_hs"
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
