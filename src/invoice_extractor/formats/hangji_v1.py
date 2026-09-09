"""Guangdong Hangji Metal (GDHJ) commercial invoice v1.

Trained on GDHJ-250980 layout text (BHC mega).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, us_float

MATCH_HINTS = {
    "filename_regex": r"GDHJ|Hangji|恒基",
    "keywords": [
        "GUANGDONG HANGJI METAL",
        "广东恒基金属",
        "Invoice No : GDHJ",
        "FOB SHUNDE",
    ],
}

NOTES = "Guangdong Hangji Metal commercial invoice; seed from GDHJ-250980"

RULES_JSON = {
    "id": "hangji_v1",
    "header": {
        "invoice_no": r"Invoice\s+No\s*:\s*(GDHJ-?\d+)",
        "amount": r"TOTAL\s*:\s*[\d,]+\s+([\d,.]+)",
        "incoterm": r"(FOB\s+SHUNDE(?:,\s*CHINA)?)",
        "pkg": r"(?:Say Total\s*:\s*|TOTAL\s*:\s*)(\d+)\s*PALLETS?",
        "gw": r"TOTAL\s*:\s*\d+\s*PALLETS?\s+[\d,]+\s+[\d,]+\s+[\d,.]+?\s+([\d,.]+)",
    },
}

_LINE = re.compile(
    r"^\s*(?P<item>\d+)\s+(?P<po>P\d+)\s+(?P<line>\d+)\s+(?P<part>\S+)\s+"
    r"(?P<desc>.+?)\s+(?P<qty>[\d,]+)\s+(?P<price>[\d.]+)\s+(?P<amt>[\d,.]+)\s*$",
    re.MULTILINE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "GDHJ" in fn or "HANGJI" in fn or "恒基" in filename:
        score += 0.35
    if "GUANGDONG HANGJI METAL" in text or "广东恒基金属" in text:
        score += 0.45
    if re.search(r"Invoice\s+No\s*:\s*GDHJ", text, re.I):
        score += 0.2
    if "BITZER" in text or "Ladeliste" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _commercial_chunk(text: str) -> str:
    # Stop before packing list / SAY TOTAL bank section still includes TOTAL line
    end = len(text)
    for marker in ("OUR BANK INFORMATION", "PACKING", "Say Total"):
        # keep TOTAL before Say Total; cut packing pages after first SAY TOTAL
        pass
    m = re.search(r"SAY TOTAL USD", text)
    if m:
        end = min(end, m.end() + 200)
    # Prefer cutting at first packing header after commercial TOTAL
    m2 = re.search(r"\n\s*PACKING\b", text[m.end() if m else 0 :])
    if m and m2:
        end = min(end, (m.end() if m else 0) + m2.start())
    return text[:end]


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    chunk = _commercial_chunk(text)
    m_inv = re.search(r"Invoice\s+No\s*:\s*(GDHJ-?\d+)", text, re.I)
    invoice_no = m_inv.group(1) if m_inv else None

    m_amt = re.search(
        r"TOTAL\s*:\s*([\d,]+)\s+([\d,.]+)",
        chunk,
        re.I,
    )
    header_qty = us_float(m_amt.group(1)) if m_amt else None
    amount = us_float(m_amt.group(2)) if m_amt else None

    m_fob = re.search(r"(FOB\s+SHUNDE(?:,\s*CHINA)?)", text, re.I)
    incoterm = m_fob.group(1).strip() if m_fob else None

    m_pkg = re.search(
        r"Say Total\s*:\s*(\d+)\s+PLYWOOD\s+PALLETS?",
        text,
        re.I,
    )
    if not m_pkg:
        m_pkg = re.search(r"TOTAL\s*:\s*(\d+)\s*PALLETS?", text, re.I)
    pkg = float(m_pkg.group(1)) if m_pkg else None

    m_gw = re.search(
        r"TOTAL\s*:\s*\d+\s*PALLETS?\s+[\d,]+\s+[\d,]+\s+([\d,.]+)\s+([\d,.]+)",
        text,
        re.I,
    )
    # columns: cartons, qty, net, gross
    m_gw2 = re.search(
        r"TOTAL\s*:\s*\d+\s*PALLETS?\s+[\d,]+\s+[\d,]+\s+([\d,.]+)\s+([\d,.]+)\s+[\d.]+\s*CBM",
        text,
        re.I,
    )
    gw = None
    if m_gw2:
        gw = us_float(m_gw2.group(2))
    elif m_gw:
        gw = us_float(m_gw.group(2))

    origin = "CN"
    m_o = re.search(r"COUNTRY OF ORIGIN\s*:\s*([A-Z]+)", text, re.I)
    if m_o:
        o = m_o.group(1).upper()
        origin = {"CHINA": "CN", "CN": "CN"}.get(o, o[:2])

    items: list[Item] = []
    seen: set[tuple] = set()
    for m in _LINE.finditer(chunk):
        key = (m.group("po"), m.group("line"), m.group("part"), m.group("qty"), m.group("amt"))
        if key in seen:
            continue
        seen.add(key)
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=m.group("part"),
                description=m.group("desc").strip(),
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
    total_qty = float(sum(it.qty or 0 for it in items)) if items else header_qty

    header = Header(
        invoice_no=invoice_no,
        total_pkg=pkg,
        gross_weight_kg=gw,
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=total_qty,
        amount=amount,
        currency="USD",
        vendor="Guangdong Hangji Metal Co., Ltd.",
        origin=origin,
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="hangji_v1",
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
