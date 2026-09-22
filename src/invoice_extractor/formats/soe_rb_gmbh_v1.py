"""SOE — Robert Bosch GmbH commercial Invoice / Invoice Copy / INV+PL v1.

Shared layout across SOE folders (70775… / 70918…): Bosch Partnumber lines,
Customs tariff no, Invoice amount, Total gross weight, Marking Pallets.
Also OCR-scanned cargo+invoice PDFs (same family; meta.text_backend=ocr/tesseract).
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
    "filename_regex": r"70775\d+|70918\d+|INV_PL_|SOE",
    "keywords": [
        "Robert Bosch GmbH",
        "Bosch Partnumber",
        "Invoice and Packing List",
        "Invoice Copy",
        "Customs tariff no",
        "Invoice amount",
        "Total gross weight",
    ],
}

NOTES = (
    "SOE Robert Bosch GmbH commercial invoice (Invoice / Invoice Copy / "
    "Invoice and Packing List). Amount = labeled Invoice amount (EUR); "
    "GW = Total gross weight (not Net); pkg = Marking summary N Pallets "
    "(OCR: prefer Marking RB … Pallets count over cargo-list misreads). "
    "Price unit 100 → unit_price = Price/100. Samples: INV_PL_70775*, "
    "707753*, 707754*, OCR 1267620500→inv 7091802382. "
    "Not BHC MY-HUB; not MA Document No./Goods Value."
)

RULES_JSON = {
    "id": "soe_rb_gmbh_v1",
    "header": {
        "invoice_no": r"Invoice\s+No\.\s*:?\s*(\d{8,12})",
        "amount": r"Invoice\s+amount\s*:?\s*(?:EUR|USD)?\s*([\d,.]+)",
        "gross_weight": r"Total\s+gross\s+weight\s*:?\s*([\d,.]+)\s*KG",
        "incoterm": r"Incoterms?\s*20\d{2}\s*[:;]?\s*([A-Z]{3}\s+[^\n]+)",
        "pkg": r"(?m)^\s*(\d+)\s*Pallets?\s*$",
    },
    "items": {
        "line": (
            r"(?m)^\s*(?P<item>\d{2})\s+"
            r"(?P<pn>\d{4}\.\d{3}\.\d{3}-[A-Za-z0-9]+)\s+"
            r"(?P<cust>\S+)\s+"
            r"(?P<qty>[\d,.]+)\s+(?P<price>[\d,.]+)\s+(?P<amt>[\d,.]+)\s*$"
        ),
        "hs": r"Customs\s+tariff\s+no\s*:?\s*(\d{6,10})",
        "origin_nw": r"(?m)^(?P<origin>[A-Z]{2})\s+([\d,.]+)\s*KG",
    },
}

# Item row (layout or OCR-collapsed)
_LINE = re.compile(
    r"(?m)^\s*(?P<item>\d{2})\s+"
    r"(?P<pn>\d{4}\.\d{3}\.\d{3}-[A-Za-z0-9]+)\s+"
    r"(?P<cust>\S+)\s+"
    r"(?P<qty>[\d,.]+)\s+(?P<price>[\d,.]+)\s+(?P<amt>[\d,.]+)\s*$"
)

# OCR often drops newlines: "01 0265… 0265… 4,928 3,251.92 160,254.62"
_LINE_INLINE = re.compile(
    r"(?P<item>\d{2})\s+"
    r"(?P<pn>\d{4}\.\d{3}\.\d{3}-[A-Za-z0-9]+)\s+"
    r"(?P<cust>[A-Za-z0-9]+)\s+"
    r"(?P<qty>[\d,.]+)\s+(?P<price>[\d,.]+)\s+(?P<amt>[\d,.]+)"
)

_DESC_PC = re.compile(
    r"(?P<desc>.+?)\s+PC\s+(?P<punit>\d+)\s+(?P<cur>[A-Z]{3})",
    re.IGNORECASE,
)

_ORIGIN_NW = re.compile(
    r"(?m)^(?:\|\s*)?(?P<origin>[A-Z]{2})\s+(?P<nw>[\d,.]+)\s*KG\b"
)

_HS = re.compile(r"Customs\s+tariff\s+no\s*:?\s*(?P<hs>\d{6,10})", re.I)

_PKG_SUMMARY = re.compile(
    r"(?m)^\s*(?P<n>\d+)\s*Pallets?\s*$",
    re.I,
)
_PKG_SUMMARY_LOOSE = re.compile(
    r"(?m)^\s*(?P<n>\d+)\s*Pallets?\b",
    re.I,
)
_PKG_CARGO = re.compile(
    r"\b(?P<n>\d+)\s+Pallets?\b",
    re.I,
)
_PKG_RB_BLOCK = re.compile(
    r"\bRB\s+\d+\s+Pallets?\b",
    re.I,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if re.search(r"70775\d+|70918\d+", fn) or "INV_PL_" in fn or "SOE" in fn:
        score += 0.25
    if "Robert Bosch GmbH" in text:
        score += 0.2
    if "Bosch Partnumber" in text or "Bosch Partnumber" in text.replace(" ", ""):
        score += 0.25
    if "Invoice and Packing List" in text or "Invoice Copy" in text:
        score += 0.2
    if "Customs tariff no" in text or "Customs Tarif" in text:
        score += 0.15
    if re.search(r"Invoice\s+amount", text, re.I):
        score += 0.1
    if "Total gross weight" in text:
        score += 0.1
    # Penalize lookalikes
    if "Bosch Home Comfort Supply" in text or "MY-HUB FINANCE" in text:
        score -= 0.6
    if "Power Tools GmbH" in text:
        score -= 0.5
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    if "Billing Document" in text and re.search(r"\bAK\d{8}\b", text):
        score -= 0.5
    if "Document No." in text and "Goods Value" in text and "Bosch Partnumber" not in text:
        score -= 0.4
    if "AIR WAYBILL" in text.upper() and "Bosch Partnumber" not in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _invoice_no(text: str) -> str | None:
    m = re.search(r"Invoice\s+No\.\s*[:+]?\s*(\d{8,12})", text, re.I)
    return m.group(1) if m else None


def _invoice_date(text: str) -> str | None:
    m = re.search(r"Date\s+Invoice\s*[:>]?\s*(\d{2}\.\d{2}\.\d{4})", text, re.I)
    return de_date_to_iso(m.group(1)) if m else None


def _amount_currency(text: str) -> tuple[float | None, str | None]:
    m = re.search(
        r"Invoice\s+amount\s*:?\s*(?:(?P<cur>EUR|USD|JPY)\s+)?"
        r"(?P<amt>[\d,.]+)",
        text,
        re.I,
    )
    if not m:
        m = re.search(
            r"Value\s+of\s+goods\s*:?\s*(?P<cur>EUR|USD|JPY)\s+(?P<amt>[\d,.]+)",
            text,
            re.I,
        )
    if not m:
        return None, None
    cur = (m.group("cur") or "EUR").upper()
    try:
        return us_float(m.group("amt")), cur
    except ValueError:
        return None, cur


def _gross_weight(text: str) -> float | None:
    m = re.search(
        r"Total\s+gross\s+weight\s*:?\s*([\d,.]+)\s*KG",
        text,
        re.I,
    )
    if m:
        try:
            return us_float(m.group(1))
        except ValueError:
            pass
    return None


def _incoterm(text: str) -> str | None:
    m = re.search(
        r"Incoterms?\s*20\d{2}\s*[:;]?\s*([A-Z]{3}\s+[^\n|;]+)",
        text,
        re.I,
    )
    if not m:
        return None
    return re.sub(r"\s+", " ", m.group(1)).strip()[:60]


def _packages(text: str) -> float | None:
    # Prefer trailing Marking summary "N   Pallets" (last occurrence)
    hits = list(_PKG_SUMMARY.finditer(text))
    if hits:
        try:
            return float(hits[-1].group("n"))
        except ValueError:
            pass
    # "2Pallets" / "2 Pallets" mid-line at end of marking
    hits = list(_PKG_SUMMARY_LOOSE.finditer(text))
    # Filter out Marking line "RB … Pallets" (no leading count only)
    clean = []
    for h in hits:
        start = h.start()
        line_start = text.rfind("\n", 0, start) + 1
        prefix = text[line_start:start]
        if re.search(r"\bRB\b", prefix, re.I):
            continue
        clean.append(h)
    if clean:
        try:
            return float(clean[-1].group("n"))
        except ValueError:
            pass
    # Prefer Invoice Marking "RB … Pallets" block count over cargo-list
    # OCR (e.g. 1267620500 misread as "12 Pallets" when Marking has 11).
    n_blocks = len(_PKG_RB_BLOCK.findall(text))
    if n_blocks >= 1:
        return float(n_blocks)
    # Cargo-list / transport OCR last resort: "1267620500 N Pallets …"
    m = re.search(
        r"\d{7,12}\s+(?P<n>\d+)\s+Pallets?\b.{0,40}?([\d,.]+)",
        text,
        re.I,
    )
    if m:
        try:
            return float(m.group("n"))
        except ValueError:
            pass
    # Cargo-list footer "Number of package: N" / "PAL: N"
    m = re.search(r"Number\s+of\s+package\s*:?\s*(?P<n>\d+)", text, re.I)
    if m:
        try:
            return float(m.group("n"))
        except ValueError:
            pass
    m = re.search(r"\bPAL\s*:\s*(?P<n>\d+)\b", text, re.I)
    if m:
        try:
            return float(m.group("n"))
        except ValueError:
            pass
    return None


def _parse_items(text: str, invoice_no: str | None, currency: str | None) -> list[Item]:
    items: list[Item] = []
    seen: set[tuple] = set()

    matches = list(_LINE.finditer(text))
    if not matches:
        matches = list(_LINE_INLINE.finditer(text))

    for m in matches:
        key = (m.group("pn"), m.group("qty"), m.group("amt"))
        if key in seen:
            continue
        seen.add(key)
        # Look ahead ~400 chars for desc / origin / HS
        window = text[m.end() : m.end() + 450]
        desc = None
        unit = "PC"
        price_unit = 100.0
        cur = currency
        dm = _DESC_PC.search(window)
        if dm:
            desc = re.sub(r"\s+", " ", dm.group("desc")).strip(" |")
            try:
                price_unit = float(dm.group("punit"))
            except ValueError:
                price_unit = 100.0
            cur = (dm.group("cur") or cur or "EUR").upper()
        om = _ORIGIN_NW.search(window)
        origin = om.group("origin") if om else None
        hm = _HS.search(window)
        hs = hm.group("hs") if hm else None
        try:
            qty = us_float(m.group("qty"))
            price = us_float(m.group("price"))
            amt = us_float(m.group("amt"))
        except ValueError:
            continue
        unit_price = price / price_unit if price_unit else price
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=m.group("pn"),
                description=desc,
                qty=qty,
                unit=unit,
                unit_price=round(unit_price, 6),
                amount=amt,
                origin=origin,
                hs_code=hs,
                currency=cur,
            )
        )
    return items


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    inv = _invoice_no(text)
    amount, currency = _amount_currency(text)
    items = _parse_items(text, inv, currency)
    # Fallback HS from Customs Tarif summary if line HS missing
    if items and any(not it.hs_code for it in items):
        summary_hs = re.findall(
            r"(?m)^(?:\|\s*)?(\d{8})\s+[\d,.]+\s+[\d,.]+\s*(?:EUR|USD)?",
            text,
        )
        if len(summary_hs) == 1:
            for it in items:
                if not it.hs_code:
                    it.hs_code = summary_hs[0]

    h = Header(
        invoice_no=inv,
        invoice_date=_invoice_date(text),
        amount=amount,
        currency=currency or ("EUR" if amount is not None else None),
        gross_weight_kg=_gross_weight(text),
        total_pkg=_packages(text),
        incoterm=_incoterm(text),
        item_line_count=len(items) if items else None,
        total_quantity=sum(it.qty or 0.0 for it in items) if items else None,
        vendor="Robert Bosch GmbH",
    )
    # Document-level HS/origin when uniform
    hs_set = {it.hs_code for it in items if it.hs_code}
    if len(hs_set) == 1:
        h.hs_code = next(iter(hs_set))
    ori_set = {it.origin for it in items if it.origin}
    if len(ori_set) == 1:
        h.origin = next(iter(ori_set))

    return ExtractResult(
        header=h,
        items=items,
        meta=Meta(
            source_file=path,
            text_backend=backend,
            format_id="soe_rb_gmbh_v1",
            confidence="rules",
            needs_ocr=needs_ocr,
            labeled_amount=amount,
            labeled_amount_label="Invoice amount",
            notes=NOTES if not items else None,
        ),
    )
