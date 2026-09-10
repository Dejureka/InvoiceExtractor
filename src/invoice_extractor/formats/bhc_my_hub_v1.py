"""Bosch Home Comfort Supply (M) Sdn. Bhd. — MY-HUB commercial invoice v1.

New BHC style (2026 samples): PART NO / QUANTITIES / TOTALS in USD.
No packing list on these PDFs — soft-missing total_pkg / gross_weight is OK.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import (
    ExtractResult,
    Header,
    Item,
    Meta,
    de_date_to_iso,
    us_float,
)

MATCH_HINTS = {
    "filename_regex": r"INV_9027|TA2608|902745",
    "keywords": [
        "Bosch Home Comfort Supply",
        "Invoice Number",
        "TOTALS:",
        "PART NO",
        "MY-HUB FINANCE",
    ],
}

NOTES = (
    "BHC MY-HUB Supply Malaysia invoice (not BITZER Versanddokument). "
    "Soft-missing packing/GW OK. Samples: TA2608B2-*_INV_902745*.PDF."
)

RULES_JSON = {
    "id": "bhc_my_hub_v1",
    "header": {
        "invoice_no": r"Invoice Number:\s*(\d{8,12})",
        "amount": r"TOTALS:\s*([\d,.]+)",
        "incoterm": r"\b(CIF|FOB|FCA|CFR|CIP|EXW|DAP|DDP)\s+([A-Za-z][^\n]{0,30})",
        "currency": "USD",
    },
}

_COO = r"Thailand|Malaysia|China|Vietnam|Japan|India|Taiwan|Indonesia"
_LINE = re.compile(
    r"^\s*(?P<pn>[A-Z0-9]{5,12}[A-Z]?)\s+(?P<desc>.+?)\s+"
    r"(?:(?P<coo>" + _COO + r")\s+)?"
    r"(?P<po>P\d+)\s+(?P<line>\d+)\s+"
    r"(?P<qty>[\d,.]+)\s*(?:PCS)?\s+"
    r"(?P<price>[\d,.]+)\s+(?P<amt>[\d,.]+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
# PCS wrapped to next line
_LINE_BROKEN = re.compile(
    r"^\s*(?P<pn>[A-Z0-9]{5,12}[A-Z]?)\s+(?P<desc>.+?)\s+"
    r"(?:(?P<coo>" + _COO + r")\s+)?"
    r"(?P<po>P\d+)\s+(?P<line>\d+)\s+"
    r"(?P<qty>[\d,.]+)\s+(?P<price>[\d,.]+)\s+(?P<amt>[\d,.]+)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "902745" in fn or "INV_" in fn or "TA2608" in fn:
        score += 0.3
    if "Bosch Home Comfort Supply" in text:
        score += 0.4
    if "MY-HUB FINANCE" in text or "TOTALS:" in text:
        score += 0.2
    if "PART NO" in text and "QUANTITIES" in text:
        score += 0.15
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    if "Power Tools GmbH" in text:
        score -= 0.4
    return max(0.0, min(score, 1.0))


def _invoice_no(text: str) -> str | None:
    # Layout: label row then value row under "Invoice Number:"
    m = re.search(
        r"Invoice Number:\s*Invoice Date:[^\n]*\n\s*\S[^\n]{0,80}?\b(\d{10})\b\s+(\d{2}\.\d{2}\.\d{4})",
        text,
    )
    if m:
        return m.group(1)
    m = re.search(r"Invoice Number:\s*(\d{8,12})", text)
    if m:
        return m.group(1)
    # filename-style fallback in body / supplier ref page stamp
    m = re.search(r"\b(9027\d{6})\b", text)
    return m.group(1) if m else None


def _invoice_date(text: str) -> str | None:
    # Same line as invoice no: "9027451705 ... 17.08.2026 ... 1/2"
    m = re.search(r"\b\d{10}\b\s+(\d{2}\.\d{2}\.\d{4})\s+\d+/\d+", text)
    if m:
        return de_date_to_iso(m.group(1))
    m = re.search(r"\b(\d{2}\.\d{2}\.\d{4})\b", text)
    return de_date_to_iso(m.group(1)) if m else None


def _totals(text: str) -> float | None:
    m = re.search(r"TOTALS:\s*([\d,.]+)", text)
    return us_float(m.group(1)) if m else None


def _incoterm(text: str) -> str | None:
    m = re.search(
        r"\b(CIF|FOB|FCA|CFR|CIP|EXW|DAP|DDP)\s+([A-Za-z][A-Za-z /,]{0,40})",
        text,
    )
    if not m:
        return None
    return f"{m.group(1)} {m.group(2).strip()}"


def _parse_items(
    text: str, invoice_no: str | None, currency: str | None
) -> list[Item]:
    items: list[Item] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _LINE.match(line)
        consumed = 1
        if not m:
            m2 = _LINE_BROKEN.match(line)
            if (
                m2
                and i + 1 < len(lines)
                and re.search(r"^\s*PCS\s*$", lines[i + 1], re.I)
            ):
                m = m2
                consumed = 2
        if not m:
            i += 1
            continue
        desc = re.sub(r"\s{2,}", " ", m.group("desc")).strip()
        # peel parenthetical continuation on next line if present
        nxt = i + consumed
        if nxt < len(lines) and re.match(r"^\s*\(", lines[nxt]):
            extra = lines[nxt].strip()
            desc = f"{desc} {extra}".strip()
        coo = m.group("coo")
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=m.group("pn"),
                description=desc or None,
                qty=us_float(m.group("qty")),
                unit="PCS",
                unit_price=us_float(m.group("price")),
                amount=us_float(m.group("amt")),
                origin=coo.title() if coo else None,
                hs_code=None,
                currency=currency,
            )
        )
        i += consumed
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
    amount = _totals(text)
    currency = "USD"
    incoterm = _incoterm(text)
    items = _parse_items(text, invoice_no, currency)
    total_qty = sum(it.qty or 0.0 for it in items) if items else None
    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=None,  # soft-missing packing OK
        gross_weight_kg=None,
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=float(total_qty) if total_qty is not None else None,
        amount=amount,
        currency=currency,
        vendor="Bosch Home Comfort Supply (M) Sdn. Bhd.",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="bhc_my_hub_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="TOTALS",
        notes="soft-missing packing/GW OK for this format",
    )
    if needs_ocr or not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
