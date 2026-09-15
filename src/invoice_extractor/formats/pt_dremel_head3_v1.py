"""PT Dremel / PPT US invoice — head3 layout (Invoice No:).

VBA: PT_PDFextractDremel_head3 / PT_Dremel_Declaration_head3.
Distinct from PT Gloria (Power Tools GmbH / Net invoiced value of goods).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import (
    ExtractResult,
    Header,
    Item,
    Meta,
    us_float,
)

MATCH_HINTS = {
    "filename_regex": r"40-D-.*PT|90-DSV-.*PT|P13\.|Dremel|Dremael|PPT",
    "keywords": [
        "Invoice No:",
        "Origin/Tariff Code",
        "Bosch Material No.",
        "Total:",
    ],
}

NOTES = (
    "PT Dremel head3 (US Tool Corp commercial invoice). "
    "Anchors: Invoice No: / Origin/Tariff Code / Total: / Bosch Material No. "
    "VBA PT_PDFextractDremel_head3 + PT_Dremel_Declaration_head3. "
    "HS required per line (hard_check). Soft-missing Packages/G.W. OK "
    "(these PDFs often omit packing GW). "
    "Page-break: desc+Origin may continue after next-page header."
)

RULES_JSON = {
    "id": "pt_dremel_head3_v1",
    "header": {
        "invoice_no": r"Invoice\s+No:\s+(\d{6,12})",
        "invoice_date": r"Doc\.\s*Date:\s+(\d{2}/\d{2}/\d{4})",
        "amount": r"Total:\s+([\d,]+\.\d{2})",
        "incoterm": r"\b(FCA|FOB|CIF|CIP|EXW|DDP|DAP|CFR)\b\s+([A-Za-z][^\n]{0,40})",
        "currency": r"Total amount\s*\n\s*(USD|EUR|CNY|GBP)",
    },
    "items": {
        "line": (
            r"([A-Z0-9]\.\d{3}\.[A-Za-z0-9]{3}\.[A-Za-z0-9]{3})"
            r"\s+(\d[\d,]*)\s+(EA|ST|PC)\s+([\d,.]+)\s+([\d,.]+)"
        ),
        "origin_hs": r"Origin/Tariff Code:\s*([A-Z]{2})\s+(\d{6,12})",
    },
}

_MAT = re.compile(
    r"(?P<mat>[A-Z0-9]\.\d{3}\.[A-Za-z0-9]{3}\.[A-Za-z0-9]{3})"
    r"\s+(?P<qty>\d[\d,]*)\s+(?P<uom>EA|ST|PC)\s+"
    r"(?P<price>\d[\d,]*\.\d{2})\s+(?P<amt>\d[\d,]*\.\d{2})",
    re.IGNORECASE,
)

_ORIGIN_HS = re.compile(
    r"Origin/Tariff Code:\s*(?P<origin>[A-Z]{2})\s+(?P<hs>\d{6,12})",
    re.IGNORECASE,
)

_NOISE = re.compile(
    r"^(Ship-To:|Bill-To:|Robert Bosch|Page\b|INVOICE\b|Document Number|"
    r"Doc\.\s*Date|Transport No|Customer No|Account No|Bosch Material|"
    r"Description\b|No\.1,|6F\.|TAIWAN\b|NEW TAIPEI|TAOYUAN|TAIPEH|"
    r"Sec 1|Dahua|Sold-to|Your Contact|Departure|Dispatch|"
    r"\d{5}\s|22449|10491|338013|UNITED STATES)",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if re.search(r"40-D-.*PT|90-DSV-.*PT|P13\.|DREMEL|DREMAEL|PPT", fn, re.I):
        score += 0.2
    if re.search(r"Invoice\s+No:", text):
        score += 0.35
    if "Origin/Tariff Code" in text:
        score += 0.25
    if "Bosch Material No." in text and re.search(r"Total:\s+[\d,]", text):
        score += 0.2
    # major layout discriminators vs Gloria / head5
    if "Robert Bosch Power Tools GmbH" in text:
        score -= 0.6
    if "Net invoiced value of goods" in text:
        score -= 0.5
    if "Bosch Document Number" in text:
        score -= 0.5
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _us_date_to_iso(d: str) -> str | None:
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})$", (d or "").strip())
    if not m:
        return None
    mm, dd, yyyy = m.groups()
    return f"{yyyy}-{mm}-{dd}"


def _invoice_no(text: str) -> str | None:
    m = re.search(r"Invoice\s+No:\s+(\d{6,12})", text)
    return m.group(1) if m else None


def _invoice_date(text: str) -> str | None:
    m = re.search(r"Doc\.\s*Date:\s+(\d{2}/\d{2}/\d{4})", text)
    return _us_date_to_iso(m.group(1)) if m else None


def _amount(text: str) -> float | None:
    m = re.search(r"Total:\s+([\d,]+\.\d{2})", text)
    return us_float(m.group(1)) if m else None


def _currency(text: str) -> str | None:
    m = re.search(
        r"Total amount\s*\n[^\n]*\n?\s*(USD|EUR|CNY|GBP)\b",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).upper()
    # column header often "USD … USD" under Total amount
    m = re.search(
        r"Price\s*/\s*Unit\s+Total amount\s*\n\s*Description\s+(USD)\b",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).upper()
    if re.search(r"\bUSD\b", text):
        return "USD"
    return None


def _incoterm(text: str) -> str | None:
    # Prefer term near Total: footer (e.g. "FCA West Memphis")
    m = re.search(
        r"Total:\s+[\d,]+\.\d{2}\s*\n\s*"
        r"(FCA|FOB|CIF|CIP|EXW|DDP|DAP|CFR)\s+([A-Za-z][^\n]{0,40})",
        text,
        re.IGNORECASE,
    )
    if m:
        return f"{m.group(1).upper()} {m.group(2).strip()}"
    m = re.search(
        r"\b(FCA|FOB|CIF|CIP|EXW|DDP|DAP|CFR)\b\s+([A-Za-z][^\n*]{0,40})",
        text,
    )
    if not m:
        return None
    place = m.group(2).strip()
    if place.lower().startswith("west") or place[0].isupper():
        return f"{m.group(1)} {place}".strip()
    return m.group(1)


def _is_noise(line: str) -> bool:
    t = line.strip()
    if not t:
        return True
    if _NOISE.search(t):
        return True
    if re.match(r"^\d{5,}\b", t):  # bare zip / long nums
        return True
    return False


def _parse_items(
    text: str, invoice_no: str | None, currency: str | None
) -> list[Item]:
    items: list[Item] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _MAT.search(line)
        if not m:
            continue
        mat = m.group("mat")
        qty = us_float(m.group("qty"))
        price = us_float(m.group("price"))
        amt = us_float(m.group("amt"))
        uom = m.group("uom").upper()
        if uom == "PC":
            uom = "PCS"

        origin = None
        hs = None
        desc = None
        # Look ahead past page headers (Origin/desc may land on next page)
        for j in range(i + 1, min(i + 45, len(lines))):
            if _MAT.search(lines[j]):
                break
            om = _ORIGIN_HS.search(lines[j])
            if om:
                origin = om.group("origin").upper()
                hs = om.group("hs")
                for k in range(j - 1, i, -1):
                    if _is_noise(lines[k]):
                        continue
                    # skip Sales Text jammed lines still usable as desc
                    desc = re.sub(r"\s{2,}", " ", lines[k]).strip()
                    desc = re.sub(r"\s+Sales Text:.*$", "", desc).strip()
                    if len(desc) > 80:
                        desc = desc[:80].rsplit(" ", 1)[0]
                    break
                break

        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=mat,
                description=desc or None,
                qty=qty,
                unit=uom,
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
    amount = _amount(text)
    currency = _currency(text)
    incoterm = _incoterm(text)
    items = _parse_items(text, invoice_no, currency)
    total_qty = sum(it.qty or 0.0 for it in items) if items else None

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=None,  # soft-missing
        gross_weight_kg=None,  # soft-missing (no Gross on head3 samples)
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=float(total_qty) if total_qty is not None else None,
        amount=amount,
        currency=currency,
        vendor="Robert Bosch Tool Corporation",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="pt_dremel_head3_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="Total:",
    )
    if needs_ocr or not invoice_no:
        meta.confidence = "needs_gold"
        meta.needs_gold = True

    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
