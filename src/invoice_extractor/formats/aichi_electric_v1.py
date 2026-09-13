"""Aichi Electric Co., Ltd. — invoice + packing sheet v1.

Combined PDF (INVOICE then PACKING SHEET FOR EXPORT SHIPMENT). Family keyed on
Aichi Electric stator/rotor layout (AETW…), not one-id-per-vendor.
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
    "filename_regex": r"IV\s*PL|AETW|AICHI",
    "keywords": [
        "AICHI ELECTRIC",
        "FOB NAGOYA",
        "PACKING SHEET FOR EXPORT SHIPMENT",
        "STATOR",
        "ROTOR",
    ],
}

NOTES = (
    "Aichi Electric combined invoice + packing sheet. "
    "PN = DWG No.; currency JPY; amount = Total FOB Nagoya. "
    "Sample: IV PL.pdf / AETW26012 (case3)."
)

RULES_JSON = {
    "id": "aichi_electric_v1",
    "header": {
        "invoice_no": r"INVOICE NO\.\s*(AETW\d+)",
        "amount": r"Total FOB Nagoya.*?JPY\s*([\d,]+)",
        "incoterm": r"FOB NAGOYA",
        "pkg": r"(\d+)\s+PALLETS",
        "gw": r"(\d+)\s+PALLETS.*?([\d,]+)\s*KG",
        "currency": "JPY",
    },
}

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# e.g. P10061729-20    2NE12586A    STATOR    120 PCS. JPY   8,702 /PC. JPY   1,044,240
_LINE = re.compile(
    r"(?P<po>P\d+(?:-\d+)?)\s+"
    r"(?P<pn>[A-Z0-9]{6,14})\s+"
    r"(?P<desc>STATOR|ROTOR|OTHER|[A-Z][A-Z /-]{2,30}?)\s+"
    r"(?P<qty>[\d,]+)\s*PCS\.?\s*JPY\s+"
    r"(?P<price>[\d,]+)\s*/\s*PC\.?\s*JPY\s+"
    r"(?P<amt>[\d,]+)",
    re.IGNORECASE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "AICHI" in fn or "AETW" in fn or re.search(r"IV\s*PL", fn):
        score += 0.3
    if "AICHI ELECTRIC" in text:
        score += 0.5
    if re.search(r"\bAETW\d+\b", text):
        score += 0.15
    if "PACKING SHEET FOR EXPORT SHIPMENT" in text:
        score += 0.1
    if "FOB NAGOYA" in text.upper() or "FOB Nagoya" in text:
        score += 0.1
    if "BITZER" in text or "MY-HUB FINANCE" in text or "QINGDAO HISENSE" in text:
        score -= 0.5
    if "NIDEC TECHNO" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _invoice_chunk(text: str) -> str:
    m = re.search(r"PACKING SHEET FOR EXPORT SHIPMENT", text, re.I)
    return text[: m.start()] if m else text


def _packing_chunk(text: str) -> str:
    m = re.search(r"PACKING SHEET FOR EXPORT SHIPMENT", text, re.I)
    return text[m.start() :] if m else ""


def _aichi_date_to_iso(d: str) -> str | None:
    """``25-Aug-26`` / ``28-Aug-26`` → ISO (assume 20xx)."""
    m = re.match(r"(\d{1,2})-([A-Za-z]{3})-(\d{2})$", (d or "").strip())
    if not m:
        return None
    dd, mon_s, yy = m.groups()
    mon = _MONTHS.get(mon_s.lower())
    if not mon:
        return None
    year = 2000 + int(yy)
    return f"{year:04d}-{mon:02d}-{int(dd):02d}"


def _parse_items(chunk: str, invoice_no: str | None) -> list[Item]:
    items: list[Item] = []
    for m in _LINE.finditer(chunk):
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=m.group("pn").strip(),
                description=m.group("desc").strip().title(),
                qty=us_float(m.group("qty")),
                unit="PCS",
                unit_price=us_float(m.group("price")),
                amount=us_float(m.group("amt")),
                origin="Japan",
                hs_code=None,
                currency="JPY",
            )
        )
    return items


def _pkg_gw(packing: str) -> tuple[float | None, float | None]:
    m = re.search(
        r"(?im)^\s*(\d+)\s+PALLETS?\b[^\n]*?([\d,]+)\s*KG\s*$",
        packing,
    )
    if m:
        return float(m.group(1)), us_float(m.group(2))
    return None, None


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    inv_chunk = _invoice_chunk(text)
    pack_chunk = _packing_chunk(text)

    m_inv = re.search(
        r"INVOICE NO\.\s*\n?\s*(AETW\d+)",
        text,
        re.I,
    )
    if not m_inv:
        m_inv = re.search(r"\b(AETW\d+)\b", text)
    invoice_no = m_inv.group(1) if m_inv else None

    m_date = re.search(
        r"INVOICE DATE\s*\n[^\n]*?\b(\d{1,2}-[A-Za-z]{3}-\d{2})\b",
        text,
        re.I,
    )
    if not m_date:
        m_date = re.search(r"\b(\d{1,2}-[A-Za-z]{3}-\d{2})\b", inv_chunk)
    invoice_date = _aichi_date_to_iso(m_date.group(1)) if m_date else None

    m_amt = re.search(
        r"Total FOB Nagoya[^\n]*?JPY\s*([\d,]+)",
        inv_chunk,
        re.I,
    )
    amount = us_float(m_amt.group(1)) if m_amt else None

    items = _parse_items(inv_chunk, invoice_no)
    total_qty = sum(it.qty or 0.0 for it in items) if items else None
    # Document may show "1463 PCS. (12 PALLETS)" — prefer labeled if present
    m_qty = re.search(r"(\d+)\s*PCS\.\s*\(\s*\d+\s+PALLETS?\)", inv_chunk, re.I)
    if m_qty:
        total_qty = us_float(m_qty.group(1))

    pkg, gw = _pkg_gw(pack_chunk)
    if pkg is None:
        m_pkg = re.search(r"\((\d+)\s+PALLETS?\)", inv_chunk, re.I)
        if m_pkg:
            pkg = float(m_pkg.group(1))

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=pkg,
        gross_weight_kg=gw,
        incoterm="FOB NAGOYA",
        item_line_count=len(items) if items else None,
        total_quantity=float(total_qty) if total_qty is not None else None,
        amount=amount,
        currency="JPY",
        vendor="AICHI ELECTRIC CO., LTD.",
        origin="Japan",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="aichi_electric_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="Total FOB Nagoya",
        source="combined",
        notes="combined INV+packing sheet; soft-missing HS OK",
    )
    if needs_ocr or not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
