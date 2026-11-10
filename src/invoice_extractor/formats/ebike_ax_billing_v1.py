"""Bosch eBike — Robert Bosch Energy and Body Systems Kft Billing Document AX… invoices.

SAP billing layout is a cousin of ``ma_ak_billing_v1``, but this is a different
legal entity and business unit: invoice numbers are AX (not AK), amounts use
EU thousands/decimals and are printed in EUR plus a HUF conversion, and
packages / G.W. come from the labelled totals (no Marking HU block).
Do not fold these into ``ma_ak_billing_v1`` — US-number and AK-only parsers
would misread this family, and vice versa.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import (
    ExtractResult,
    Header,
    Item,
    Meta,
    de_date_to_iso,
)

MATCH_HINTS = {
    "filename_regex": r"Invoice\s+AX\d{8}|AX\d{8}",
    "keywords": [
        "Robert Bosch Energy and Body Systems",
        "Billing Document",
        "Bosch Material No.",
        "Commodity Code",
        "Country of Origin",
        "Total Gross Weight",
        "FCA Miskolc",
    ],
}

NOTES = (
    "eBike Billing Document AX######## (Robert Bosch Energy and Body Systems Kft, "
    "Miskolc). PN like EB11.900.018-VE4 / 1270.016.507-VE4 / 0275.007.337-VE4; "
    "HS=Commodity Code (hard required, same policy as MA/PT/SOE); "
    "Origin=Country of Origin per line. "
    "Amounts are EU-format (18.022,42) in EUR; ignore the HUF conversion block. "
    "Labeled amount=Net value … EUR (tax-free Total value equals Net value on this batch). "
    "Unit price is per Pricing Unit (typically 100 PC on the description line); "
    "trust printed Net Value; hard_check uses item.pricing_unit. "
    "Packages/GW=printed Total Num of packages / Total Gross Weight (per invoice; "
    "this 1st batch shares consignment 0050142328 but each invoice has its own "
    "1 package and a distinct GW, so shipment_first is not applied). "
    "Samples: eBike 1st, AX00011132–AX00011149."
)

RULES_JSON = {
    "id": "ebike_ax_billing_v1",
    "header": {
        "invoice_no": r"Billing Document\s+(AX\d{8,})",
        "amount": r"Net value\s+([\d.]+,\d{2})\s+EUR",
        "incoterm": r"Incoterms\s+([^\n]+)",
        "currency": "EUR",
        "packages": r"Total Num of packages\s+(\d+)",
        "gross_weight": r"Total Gross Weight\s+([\d.,]+)\s*KG",
    },
    "items": {
        "line": (
            r"(\d{1,3})\s+([A-Z0-9]+(?:\.[A-Z0-9]+)+-[A-Z0-9]+)\s+"
            r"([\d.]+)\s+PC\s+([\d.]+,\d{2})\s+([\d.]+,\d{2})"
        ),
    },
}

# Item header: pos + dotted/hyphen PN + qty UoM + EU unit price + EU net value
_ITEM = re.compile(
    r"^(?P<pos>\d{1,3})\s+(?P<pn>[A-Z0-9]+(?:\.[A-Z0-9]+)+(?:-[A-Z0-9]+)?)\s+"
    r"(?P<qty>[\d.]+)\s+(?P<uom>PC|EA|SET|SA|PCE)\s+"
    r"(?P<price>[\d.]+,\d{2})\s+(?P<amt>[\d.]+,\d{2})"
    r"(?:\s+[\d,]+%\s+[\d.,]+)?\s*$",
)
_DESC_PU = re.compile(
    r"^\s+(?!Customer|Commodity|Country|EAN|Net Weight|Gross Weight|Batch|"
    r"Delivery Number|Your Ord|Our Ord|Handling|Net Val|POS-no)"
    r"(?P<desc>[A-Za-z].*?)\s+(?P<pu>\d+)\s+PC\s*$"
)
_HS = re.compile(r"Commodity\s+Code\s+(\d{6,12})", re.I)
_COO = re.compile(r"Country of Origin\s+([A-Z]{2})\b", re.I)
_NW = re.compile(r"Net Weight\s+([\d.,]+)\s*KG", re.I)
_PAGE_NOISE = re.compile(
    r"Bank Details|Registered Office|Managing Directors|Bosch Contacts|"
    r"Bill to Party|Billing Document|Item\s+Bosch Material|"
    r"The document is valid|Chairman/|Robert Bosch Energy",
    re.I,
)
_TOTAL_NW = re.compile(r"Total Net Weight\s+([\d.,]+)\s*KG", re.I)


def ebike_float(s: str) -> float:
    """EU numbers as printed on eBike AX invoices.

    ``18.022,42`` / ``75,425`` / ``107,000`` use a decimal comma (optional
    thousand dots). ``1.100`` and ``1.640.493`` (no comma) are thousand groups,
    not US decimals — qty 1.100 is 1100 PC, not 1.1.
    """
    s = (s or "").strip().replace(" ", "").replace("\u00a0", "")
    if not s:
        raise ValueError("empty number")
    if "," in s:
        return float(s.replace(".", "").replace(",", "."))
    if "." in s:
        parts = s.split(".")
        if len(parts) >= 2 and all(p.isdigit() for p in parts) and all(
            len(p) == 3 for p in parts[1:]
        ):
            return float("".join(parts))
        return float(s)
    return float(s)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if re.search(r"AX\d{8}", fn):
        score += 0.3
    if re.search(r"Billing Document\s+AX\d+", text):
        score += 0.4
    if "Energy and Body Systems" in text:
        score += 0.3
    if "Bosch Material No." in text or "Commodity Code" in text:
        score += 0.15
    if re.search(r"Net value\s+[\d.]+,\d{2}\s+EUR", text):
        score += 0.1
    # Not the MA AK / Document-No families, PT, or BITZER
    if re.search(r"Billing Document\s+AK\d+", text) and not re.search(
        r"Billing Document\s+AX\d+", text
    ):
        score -= 0.6
    if re.search(r"Document\s+No\.:?\s+\d{8,12}", text) and "Billing Document" not in text:
        score -= 0.5
    if "Power Tools GmbH" in text or "Net invoiced value of goods" in text:
        score -= 0.5
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _invoice_no(text: str) -> str | None:
    m = re.search(r"Billing Document\s+(AX\d{8,})", text)
    return m.group(1) if m else None


def _invoice_date(text: str) -> str | None:
    m = re.search(r"Billing Date\s+(\d{2}\.\d{2}\.\d{4})", text)
    return de_date_to_iso(m.group(1)) if m else None


def _net_value_eur(text: str) -> float | None:
    m = re.search(r"Net value\s+([\d.]+,\d{2})\s+EUR", text)
    return ebike_float(m.group(1)) if m else None


def _incoterm(text: str) -> str | None:
    m = re.search(r"Incoterms\s+([^\n]+)", text)
    if m:
        return re.sub(r"\s{2,}", " ", m.group(1)).strip() or None
    return None


def _packages_gw(text: str) -> tuple[float | None, float | None]:
    pm = re.search(r"Total Num of packages\s+(\d+)", text, re.I)
    gm = re.search(r"Total Gross Weight\s+([\d.,]+)\s*KG", text, re.I)
    pkg = float(pm.group(1)) if pm else None
    gw = ebike_float(gm.group(1)) if gm else None
    return pkg, gw


def _parse_items(text: str, invoice_no: str | None, currency: str | None) -> list[Item]:
    items: list[Item] = []
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _ITEM.match(line)
        if not m:
            continue
        desc = None
        hs = None
        origin = None
        nw = None
        pu = None
        for j in range(i + 1, min(i + 45, len(lines))):
            ln = lines[j]
            if _ITEM.match(ln):
                break
            if _PAGE_NOISE.search(ln):
                continue
            if desc is None:
                dm = _DESC_PU.match(ln)
                if dm:
                    desc = re.sub(r"\s{2,}", " ", dm.group("desc")).strip()
                    pu = float(dm.group("pu"))
            hm = _HS.search(ln)
            if hm and hs is None:
                hs = hm.group(1)
            cm = _COO.search(ln)
            if cm and origin is None:
                origin = cm.group(1)
            # Line NW only (the Total Net Weight line is after the last item)
            if re.match(r"^\s+Net Weight\b", ln):
                nm = _NW.search(ln)
                if nm and nw is None:
                    nw = ebike_float(nm.group(1))
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=m.group("pn"),
                description=desc,
                qty=ebike_float(m.group("qty")),
                unit=m.group("uom"),
                unit_price=ebike_float(m.group("price")),
                amount=ebike_float(m.group("amt")),
                origin=origin,
                hs_code=hs,
                currency=currency,
                net_weight=nw,
                pricing_unit=pu,
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
    amount = _net_value_eur(text)
    currency = "EUR" if amount is not None or re.search(r"\bEUR\b", text) else None
    incoterm = _incoterm(text)
    pkg, gw = _packages_gw(text)
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
        vendor="Robert Bosch Energy and Body Systems Kft (eBike)",
    )
    notes: list[str] = []
    if items and any(not it.hs_code for it in items):
        notes.append("missing_line_hs")
    tm = _TOTAL_NW.search(text)
    if tm and items:
        total_nw = ebike_float(tm.group(1))
        over = [
            it.part_no
            for it in items
            if it.net_weight is not None and it.net_weight - total_nw > 0.05
        ]
        if over:
            notes.append(
                "line_nw_exceeds_total_nw:" + ",".join(p for p in over if p)
            )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="ebike_ax_billing_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=amount,
        labeled_amount_label="Net value EUR",
        notes="; ".join(notes) or None,
    )
    if needs_ocr or not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
