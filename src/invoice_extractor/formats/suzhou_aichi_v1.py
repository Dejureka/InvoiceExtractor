"""Suzhou Aichi Technology (苏州爱知) — combined INV+PKL v1 (OCR-friendly).

BHC 3rd case1: ``SATJG26010.pdf`` (scan). Distinct from Japan ``aichi_electric_v1`` (AETW).
BHC 4th case2: ``SATJG26011.pdf`` (scan) — STATOR + ROTOR lines, PN on the line
below the commodity (``AE75D1S C(2NE34604D)``), FOB SHANGHAI, 12 plywood pallets.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import ExtractResult, Header, Item, Meta, us_float

MATCH_HINTS = {
    "filename_regex": r"SATJG|SUZHOU.?AICHI|苏州爱知",
    "keywords": [
        "SUZHOU AICHI TECHNOLOGY",
        "SATJG",
        "ROTOR",
        "STATOR",
        "FOB SHENZHEN",
        "FOB SHANGHAI",
    ],
}

NOTES = (
    "Suzhou Aichi Technology combined INV+PKL (SATJG…). OCR OK on BHC 3rd case1. "
    "Not Japan Aichi Electric (AETW). BHC 4th case2 (SATJG26011): ROTOR + STATOR "
    "lines; PN may sit on the next OCR line; incoterm read from the page "
    "(FOB SHENZHEN / FOB SHANGHAI — no default); labeled TOTAL amount used for the "
    "hard check when OCR-readable (else sum(lines)); GW = Gross column of the "
    "packing TOTAL row (NOT Net); pkg = TOTAL N Plywood Pallets, else sum of "
    "packing rows. OCR money: '56, 92' = 56.92, '36, 770. 32' = 36770.32."
)

RULES_JSON = {
    "id": "suzhou_aichi_v1",
    "header": {
        "invoice_no": r"INVOICE\s+NO\.?\s*(SATJG\w+)",
        "amount": r"USD\s*([\d,]+\.\d{2})",
        "incoterm": r"(FOB\s+[A-Z]+)",
        "pkg": r"(\d+)\s*(?:Plywood\s+)?Pallets",
        "gw": r"([\d,]+)\s*k[ge]s",
    },
}

# OCR-tolerant line: HS + ROTOR + PN + qty + USD price + USD amt
_LINE = re.compile(
    r"(?P<hs>\d{8,10})\s+ROTOR[^\n]{0,60}?"
    r"(?P<pn>TW\d+\s*\([^)]+\)|[A-Z0-9]{5,}\([^)]+\))\s+"
    r"(?P<qty>[\d,]+)\s*p[ec]s\s+USD\s*(?P<price>[\d., ]+?)\s+"
    r"USD\s*(?P<amt>[\d., ]+?)(?=\s*$|\s{2,}|\n|TOTAL|debate|E\.|&)",
    re.IGNORECASE | re.MULTILINE,
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if "SATJG" in fn or "SUZHOU" in fn and "AICHI" in fn:
        score += 0.35
    if "SUZHOU AICHI TECHNOLOGY" in tu or "SUZHOU AICHI" in tu:
        score += 0.5
    if re.search(r"\bSATJG\w+", tu):
        score += 0.2
    if "AICHI ELECTRIC" in tu and "SUZHOU" not in tu:
        score -= 0.6
    if "AETW" in tu:
        score -= 0.5
    if "NIDEC" in tu or "BITZER" in tu or "MARUBENI" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _clean_money(s: str) -> float | None:
    """OCR money: ``56, 92`` → 56.92; ``36, 770. 32`` → 36770.32; ``18, 427. 50``."""
    s = re.sub(r"\s+", "", (s or "").strip()).rstrip(".,")
    if not s:
        return None
    if "." in s:
        s = s.replace(",", "")
    elif re.search(r",\d{2}$", s):
        # comma read for the decimal point (no '.' anywhere)
        s = s[: s.rfind(",")].replace(",", "") + "." + s[-2:]
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _only_leading_digit_differs(a: float, b: float) -> bool:
    sa, sb = f"{a:.2f}", f"{b:.2f}"
    if sa.endswith(sb) or sb.endswith(sa):
        return True  # leading digit(s) dropped
    return len(sa) == len(sb) and sa[1:] == sb[1:] and sa[0] != sb[0]


def _ocr_int(s: str) -> float | None:
    s = re.sub(r"[\s,]", "", s or "")
    return float(s) if s.isdigit() else None


# One commodity row: idx + HS + ROTOR/STATOR + (PN inline) + qty pcs USD price USD amt.
_ROW = re.compile(
    r"(?:^|\s)(?P<idx>\d{1,2})\s+(?P<hs>\d{8,10})\s*\|?\s*(?P<desc>ROTOR|STATOR)\b"
    r"(?P<mid>[^\n]{0,60}?)\s+"
    r"(?P<qty>\d[\d,]*)\s*p[ec]s\s+USD\s*(?P<price>\d[\d,. ]*?)\s+"
    r"USD\s*(?P<amt>\d[\d,. ]*\d)\s*$",
    re.IGNORECASE | re.MULTILINE,
)
_PN_TOKEN = re.compile(r"([A-Z0-9]{4,}(?:\s?[A-Z0-9])?\s*\(\s*[A-Z0-9]{6,}\s*\))", re.I)


def _pn_from(chunk: str) -> str | None:
    m = _PN_TOKEN.search(chunk or "")
    if not m:
        return None
    return re.sub(r"\s+", "", m.group(1)).upper()


def extract_from_text(
    text: str,
    *,
    source_file: str = "",
    text_backend: str = "",
    needs_ocr: bool = False,
) -> ExtractResult:
    m_inv = re.search(r"INVOICE\s+NO\.?\s*:?\s*(SATJG\w+)", text, re.I)
    if not m_inv:
        m_inv = re.search(r"\b(SATJG\w+)\b", text, re.I)
    invoice_no = m_inv.group(1).upper() if m_inv else None

    m_date = re.search(
        r"(?:DATE|日\s*期)\s*:?\s*(\d{1,2}/[A-Za-z]{3}/\d{2,4})",
        text,
        re.I,
    )
    invoice_date = m_date.group(1) if m_date else None

    # Incoterm as printed (BHC 3rd: FOB SHENZHEN; 4th: FOB SHANGHAI) — no default.
    m_inc = re.search(r"\b(FOB)\s+(SHENZHEN|SHANGHAI|SUZHOU|NINGBO|[A-Z]{4,12})\b", text)
    incoterm = f"{m_inc.group(1)} {m_inc.group(2)}".upper() if m_inc else None

    # Invoice page only (packing list repeats the commodity rows without USD).
    inv_part = re.split(r"\bPACKING\s+LIST\b", text, maxsplit=1, flags=re.I)[0]
    lines = inv_part.splitlines()
    items: list[Item] = []
    for m in _ROW.finditer(inv_part):
        pn = _pn_from(m.group("mid"))
        if pn is None:
            # PN printed on the line below the commodity (BHC 4th case2)
            line_no = inv_part.count("\n", 0, m.end())
            nxt = lines[line_no + 1] if line_no + 1 < len(lines) else ""
            pn = _pn_from(nxt)
        desc = m.group("desc").upper()
        items.append(
            Item(
                invoice_no=invoice_no,
                part_no=pn or f"{desc}-{m.group('idx')}",
                description=desc,
                qty=_ocr_int(m.group("qty")),
                unit="PCS",
                unit_price=_clean_money(m.group("price")),
                amount=_clean_money(m.group("amt")),
                hs_code=m.group("hs"),
                origin="CN",
                currency="USD",
            )
        )

    # Fallback looser lines if OCR broke HS/PN glue
    if not items:
        loose = re.compile(
            r"(ROTOR|STATOR)[^\n]{0,60}?(?P<qty>[\d,]+)\s*p[ec]s\s+USD\s*(?P<price>[\d,. ]+)\s+USD\s*(?P<amt>[\d,. ]+)",
            re.I,
        )
        for i, m in enumerate(loose.finditer(inv_part), 1):
            desc = m.group(1).upper()
            items.append(
                Item(
                    invoice_no=invoice_no,
                    part_no=f"{desc}-{i}",
                    description=desc,
                    qty=_ocr_int(m.group("qty")),
                    unit="PCS",
                    unit_price=_clean_money(m.group("price")),
                    amount=_clean_money(m.group("amt")),
                    origin="CN",
                    currency="USD",
                )
            )

    sum_lines = (
        round(sum(it.amount or 0 for it in items), 2)
        if items and all(it.amount is not None for it in items)
        else None
    )
    # Labeled TOTAL (OCR-tolerant): last money on the invoice TOTAL row,
    # e.g. "TOTAL P29 pes us 66, 150. 64" / "TOTAL Pop t00 pes sb 10, 875. 00".
    labeled = None
    m_tot = re.search(r"(?im)^\s*TOTAL\b[^\n]*?(\d{1,3}(?:,\s?\d{3})*\.\s?\d{2})\s*$", inv_part)
    if m_tot:
        labeled = _clean_money(m_tot.group(1))
    amount = sum_lines
    label = "sum(lines)"
    total_note = None
    if labeled is not None and sum_lines is not None and abs(labeled - sum_lines) <= 0.05:
        label = "TOTAL"
    elif (
        labeled is not None
        and sum_lines is not None
        and _only_leading_digit_differs(labeled, sum_lines)
    ):
        # OCR misread only the leading digit of the TOTAL ("10, 875. 00" for
        # 40,875.00, BHC 3rd case1); every other digit agrees → use the rows.
        total_note = (
            f"OCR TOTAL read {labeled:.2f} (leading digit misread); "
            f"sum(lines) {sum_lines:.2f} used"
        )
        labeled = sum_lines
    elif labeled is not None and sum_lines is not None:
        # OCR TOTAL disagrees with the rows: keep it as the label so the hard
        # check fails (do not let sum(lines) pass silently).
        label = "TOTAL"
    else:
        labeled = sum_lines

    # Packing
    pkg = None
    gw = None
    pk_part = text[len(inv_part):] or text
    m_ply = re.search(r"TOTAL\s*:?\s*(\d{1,3})\s*Plywood\s+Pallets", pk_part, re.I)
    if m_ply:
        pkg = float(m_ply.group(1))
    # Packing rows: "No. 1-9 9 Stator …" / "No. 4-7 4 ROTOR …" → sum counts
    pallet_rows = re.findall(
        r"No[.,]\s*\d+\s*-\s*\d+\s+(\d+)\s+(?:\S+\s+)?(?:ROTOR|STATOR)",
        pk_part,
        re.I,
    )
    rows_sum = float(sum(int(x) for x in pallet_rows)) if pallet_rows else None
    if pkg is None:
        pkg = rows_sum
    if pkg is None:
        m_plts = re.search(r"(\d+)\s*PLTS", text, re.I)
        if m_plts:
            pkg = float(m_plts.group(1))
    # Gross = 2nd weight on the packing TOTAL row: … 3,876 kgs 4,121 kes 4, 55M3
    num = r"\d{1,3}(?:,\s?\d{3})*"
    m_gw = re.search(
        rf"(?im)^\s*TOTAL\b[^\n]*?({num})\s*k[ge]s\s+({num})\s*k[ge]s",
        pk_part,
    )
    if m_gw:
        gw = _ocr_int(m_gw.group(2))
    if gw is None:
        weights = [_ocr_int(w) for w in re.findall(rf"({num})\s*k[ge]s", pk_part, re.I)]
        vals = [v for v in weights if v and 1000 < v < 50000]
        if vals:
            gw = max(vals)

    header = Header(
        invoice_no=invoice_no,
        invoice_date=invoice_date,
        total_pkg=pkg,
        gross_weight_kg=gw,
        incoterm=incoterm,
        item_line_count=len(items) if items else None,
        total_quantity=float(sum(it.qty or 0 for it in items)) if items else None,
        amount=amount,
        currency="USD",
        vendor="SUZHOU AICHI TECHNOLOGY CO., LTD.",
        origin="CN",
    )
    meta = Meta(
        source_file=source_file,
        text_backend=text_backend,
        format_id="suzhou_aichi_v1",
        confidence="rules",
        needs_ocr=needs_ocr,
        labeled_amount=labeled,
        labeled_amount_label=label,
        source="combined",
    )
    notes = [total_note] if total_note else []
    if rows_sum is not None and pkg is not None and rows_sum != pkg:
        notes.append(f"packing rows sum {rows_sum:g} != TOTAL pallets {pkg:g}")
    if not invoice_no or amount is None or not items:
        meta.confidence = "needs_gold"
        meta.needs_gold = True
        notes.append("OCR partial — verify amount/PN vs figure")
    elif needs_ocr:
        notes.append("OCR backend — Auditor should confirm figure vs JSON")
    meta.notes = "; ".join(notes) or None
    return ExtractResult(header=header, items=items, meta=meta)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    return extract_from_text(
        text, source_file=path, text_backend=backend, needs_ocr=needs_ocr
    )
