"""PT Dremel / PPT US invoice — head5 layout (Bosch Document Number).

VBA: PT_PDFextractDremel_head5 / PT_Dremel_Declaration_head5.
Major layout vs head3 (Invoice No: / Origin/Tariff Code).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import (
    ExtractResult,
    Header,
    Item,
    Meta,
    de_date_to_iso,
    en_date_to_iso,
    us_float,
)

MATCH_HINTS = {
    "filename_regex": r"PPT|REVISED INVOICE|DOC#|Bosch Document",
    "keywords": [
        "Bosch Document Number",
        "Robert Bosch Tool Corporation",
        "Value of Goods",
        "HSN/SAC Code",
        "Country of Origin",
    ],
}

NOTES = (
    "PT Dremel head5 (Tool Corp / Bosch Document Number). "
    "Anchors: Bosch Document Number / Value of Goods / Country of Origin + HSN/SAC. "
    "Line: PN + Mat.Net KG + qty + ST/EA + price /1 + amount. "
    "VBA PT_PDFextractDremel_head5 + PT_Dremel_Declaration_head5. "
    "G.W. = packing Totals gross (2nd KG) or labeled Gross Weight — never Net. "
    "HS required per line (hard_check)."
)

RULES_JSON = {
    "id": "pt_dremel_head5_v1",
    "header": {
        "invoice_no": r"Bosch Document Number:\s+(\d{6,12})",
        "invoice_date": r"Doc\.\s*Date:\s+(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})",
        "amount": r"Value of Goods\s+([\d,]+\.?\d*)",
        "incoterm": r"Delivery Term:\s*(FCA|FOB|CIF|CIP|EXW|DDP|DAP|CFR)\s+(.+)",
        "gross_weight": r"Totals:\s+[\d,.]+\s*KG\s+([\d,.]+\s*KG)",
    },
    "items": {
        "line": (
            r"([A-Z0-9]\.\d{3}\.[A-Za-z0-9]{3}\.[A-Za-z0-9]{3})"
            r"\s+([\d,.]+)\s*KG\s+(\d[\d,]*)\s+(EA|ST|PC)\s+"
            r"([\d,.]+)\s*/\s*\d+\s+([\d,.]+)"
        ),
        "origin_hs": r"Country of Origin:\s*([A-Za-z]{2}).+HSN/SAC Code:\s*(\d{6,12})",
    },
}

_MAT = re.compile(
    r"(?P<mat>[A-Z0-9]\.\d{3}\.[A-Za-z0-9]{3}\.[A-Za-z0-9]{3})"
    r"\s+(?P<nw>[\d,.]+)\s*KG\s+"
    r"(?P<qty>\d[\d,]*)\s+(?P<uom>EA|ST|PC)\s+"
    r"(?P<price>\d[\d,]*\.\d{2})\s*/\s*\d+\s+"
    r"(?P<amt>[\d,]+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

_ORIGIN_HS = re.compile(
    r"Country of Origin:\s*(?P<origin>[A-Za-z]{2})\s+"
    r"HSN/SAC Code:\s*(?P<hs>\d{6,12})",
    re.IGNORECASE,
)

_NOISE = re.compile(
    r"^(Ship-To:|Bill-To:|Robert Bosch|Page\b|INVOICE\b|Doc\.\s*Date|"
    r"Bosch Document|Customer No|Account No|Bosch Material|Description\b|"
    r"Delivery No:|Packing No:|Company\b|UNITED STATES|MOUNT PROSPECT|"
    r"No\.432|TAOYUAN|TAIWAN)",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "PPT" in fn or "REVISED" in fn or "DOC#" in fn:
        score += 0.15
    if "Bosch Document Number" in text:
        score += 0.4
    if "Robert Bosch Tool Corporation" in text:
        score += 0.2
    if "Value of Goods" in text and "HSN/SAC Code" in text:
        score += 0.25
    if re.search(r"Invoice\s+No:", text) and "Origin/Tariff Code" in text:
        score -= 0.5  # head3
    if "Robert Bosch Power Tools GmbH" in text:
        score -= 0.6
    if "Net invoiced value of goods" in text:
        score -= 0.5
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _invoice_no(text: str) -> str | None:
    m = re.search(r"Bosch Document Number:\s+(\d{6,12})", text)
    return m.group(1) if m else None


def _invoice_date(text: str) -> str | None:
    m = re.search(
        r"Doc\.\s*Date:\s+(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2})",
        text,
    )
    if not m:
        return None
    raw = m.group(1)
    if "-" in raw:
        return en_date_to_iso(raw) or raw
    return de_date_to_iso(raw)


def _amount(text: str) -> float | None:
    m = re.search(r"Value of Goods\s+([\d,]+\.?\d*)", text)
    if m:
        return us_float(m.group(1))
    m = re.search(r"Total Value:\s+([\d,]+\.?\d*)", text)
    return us_float(m.group(1)) if m else None


def _currency(text: str) -> str | None:
    m = re.search(
        r"Total amount\s*\n[^\n]*\b(USD|EUR|CNY|GBP)\b",
        text,
        re.IGNORECASE,
    )
    if m:
        return m.group(1).upper()
    if re.search(r"\bUSD\b", text):
        return "USD"
    return None


def _incoterm(text: str) -> str | None:
    m = re.search(
        r"Delivery Term:\s*(FCA|FOB|CIF|CIP|EXW|DDP|DAP|CFR)\s+([^\n]+)",
        text,
        re.IGNORECASE,
    )
    if not m:
        return None
    place = m.group(2).strip().rstrip(",")
    return f"{m.group(1).upper()} {place}".strip()


def _gross_weight(text: str) -> float | None:
    """Prefer packing Totals net/gross pair (2nd = Gross); never Net alone."""
    m = re.search(
        r"Totals:\s+([\d,]+\.?\d*)\s*KG\s+([\d,]+\.?\d*)\s*KG",
        text,
        re.IGNORECASE,
    )
    if m:
        return us_float(m.group(2))
    # Tariff footer: labeled Gross Weight after Totals / Net Weight block
    idx = text.rfind("Gross Weight")
    if idx < 0:
        return None
    # Prefer last labeled Gross Weight that is NOT on a Delivery/Packing line
    best = None
    for m in re.finditer(
        r"Gross Weight\s+([\d,]+\.?\d*)\s*KG",
        text,
        re.IGNORECASE,
    ):
        # skip delivery header lines that also carry Packing No
        start = max(0, m.start() - 120)
        window = text[start : m.start()]
        if "Packing No" in window or "Delivery No" in window:
            continue
        best = us_float(m.group(1))
    return best


def _total_pkg(text: str) -> float | None:
    m = re.search(
        r"Standard pallet\s+(\d+)\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if m:
        return float(m.group(1))
    # trailing Totals: N (package count)
    ms = list(
        re.finditer(r"^\s*Totals:\s+(\d+)\s*$", text, re.MULTILINE)
    )
    if ms:
        return float(ms[-1].group(1))
    return None


def _is_noise(line: str) -> bool:
    t = line.strip()
    if not t:
        return True
    return bool(_NOISE.search(t))


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
        for j in range(i + 1, min(i + 12, len(lines))):
            if _MAT.search(lines[j]):
                break
            # COO + HSN may be on one line (pdftotext layout)
            chunk = lines[j]
            if j + 1 < len(lines):
                chunk = lines[j] + " " + lines[j + 1]
            om = _ORIGIN_HS.search(chunk) or _ORIGIN_HS.search(lines[j])
            if om:
                origin = om.group("origin").upper()
                hs = om.group("hs")
                for k in range(j - 1, i, -1):
                    if _is_noise(lines[k]):
                        continue
                    desc = re.sub(r"\s{2,}", " ", lines[k]).strip()
                    if len(desc) > 80:
                        desc = desc[:80].rsplit(" ", 1)[0]
                    break
                break
            # also try if Origin alone then HSN on next
            om2 = re.search(
                r"Country of Origin:\s*([A-Za-z]{2})\s*$",
                lines[j],
                re.I,
            )
            if om2 and j + 1 < len(lines):
                hm = re.search(
                    r"HSN/SAC Code:\s*(\d{6,12})",
                    lines[j + 1],
                    re.I,
                )
                if hm:
                    origin = om2.group(1).upper()
                    hs = hm.group(1)
                    if i + 1 < j and not _is_noise(lines[i + 1]):
                        desc = lines[i + 1].strip()
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
    gw = _gross_weight(text)
    pkg = _total_pkg(text)
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
        vendor="Robert Bosch Tool Corporation",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="pt_dremel_head5_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="Value of Goods",
    )
    if needs_ocr or not invoice_no:
        meta.confidence = "needs_gold"
        meta.needs_gold = True

    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
