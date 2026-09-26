"""SOE — Robert Bosch GmbH commercial Invoice / Invoice Copy / INV+PL v1.

Shared layout across SOE folders (70775… / 70918…): Bosch Partnumber lines,
Customs tariff no, Invoice amount, Total gross weight, Marking Pallets.
Also OCR-scanned cargo+invoice PDFs (same family; meta.text_backend=ocr/tesseract).

SOE 2nd (2026-09-26) extensions — additive, v1 meaning unchanged:
- OCR Bosch PN separator noise normalised. Whitespace-only noise
  ("0263 .036.668-2U1") is a benign repair; a misread separator glyph
  ("0265.011, 097-576": ',' for '.') means the PN token itself was misread
  (57G read as 576 on the same scans), so ``items.part_no`` → needs_gold
  (value kept as read, never guessed).
- OCR only: every reading of the same PN stem in the scan (item row,
  Customer PN column, cargo list, delivery note) must agree on the suffix;
  disagreement also flags ``items.part_no`` needs_gold.
- GW fallback: Marking summary "N Pallets / Net weight … Gross weight : X KG"
  when no "Total gross weight" line is printed (7077520279).
- Origin fallback: bare country line (no Net weight) above Customs tariff no.
- pkg: typed Marking summary ": 5 cardboard pallet" before cargo-list fallbacks.
- Soft note when printed page marks "k / M" show a page missing from the PDF.
- Date/amount label OCR tolerance ("Date Invoice + 06.08.2026",
  "Invoice amount =: EUR").
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
    "Not BHC MY-HUB; not MA Document No./Goods Value. "
    "SOE 2nd: OCR PN separator repair (glyph misread → part_no needs_gold), "
    "OCR PN-suffix readings disagree → needs_gold, Marking GW fallback, bare-origin "
    "fallback, thin-text-layer OCR retry (rules_engine)."
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
# Marking summary with a package type word: ": 5 cardboard pallet" (OCR may
# prefix ':' / '|' and misread "pallet" as "pailet").
_PKG_SUMMARY_TYPED = re.compile(
    r"(?m)^[\s:|]*(?P<n>\d+)\s+cardboard\s+pa[il]{1,3}ets?\s*\|?\s*$",
    re.I,
)
_PKG_RB_BLOCK = re.compile(
    r"\bRB\s+\d+\s+Pallets?\b",
    re.I,
)


# OCR splits the Bosch PN: "01 0265 .011, 097-576 …" → "01 0265.011.097-576 …"
_PN_NOISY = re.compile(
    r"(?m)^(?P<lead>[ \t|]*\d{2}[ \t]+)"
    r"(?P<a>\d{4})[ \t]*[.,][ \t]*(?P<b>\d{3})[ \t]*[.,][ \t]*(?P<c>\d{3})"
    r"[ \t]*-[ \t]*(?P<s>[A-Za-z0-9]+)"
)

# Marking summary: "2 Pallets" then "Net weight : … KG   Gross weight : X KG"
_MARKING_GW = re.compile(
    r"(?m)^[ \t|]*\d+[ \t]*Pallets?[ \t:]*\n[ \t|]*Net\s+weight\s*[:;]\s*[\d,.]+\s*KG"
    r"\s+Gross\s+weight\s*[:;]\s*(?P<gw>[\d,.]+)\s*KG",
    re.I,
)

_ORIGIN_BARE = re.compile(r"(?m)^[ \t|]*(?P<origin>[A-Z]{2})[ \t]*$")


def normalize_ocr_partnumbers(text: str) -> tuple[str, list[str]]:
    """Repair OCR spacing/comma noise inside Bosch PN on item rows.

    Returns ``(text, misread)`` where ``misread`` lists raw PN tokens whose
    separators were misread as another glyph (',' for '.'); whitespace-only
    repairs are not listed.
    """
    misread: list[str] = []

    def _fix(m: re.Match) -> str:
        canon = f"{m.group('a')}.{m.group('b')}.{m.group('c')}-{m.group('s')}"
        raw = m.group(0)[len(m.group("lead")):]
        if re.sub(r"[ \t]", "", raw) != canon:
            misread.append(re.sub(r"\s+", " ", raw).strip())
        return m.group("lead") + canon

    return _PN_NOISY.sub(_fix, text), misread


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
    m = re.search(r"Date\s+Invoice\s*[:>+=;]?\s*(\d{2}\.\d{2}\.\d{4})", text, re.I)
    return de_date_to_iso(m.group(1)) if m else None


def _amount_currency(text: str) -> tuple[float | None, str | None]:
    m = re.search(
        r"Invoice\s+amount\s*[:=;]*\s*(?:(?P<cur>EUR|USD|JPY)\s+)?"
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
    # No "Total gross weight" line: Marking summary under "N Pallets".
    hits = list(_MARKING_GW.finditer(text))
    if hits:
        try:
            return us_float(hits[-1].group("gw"))
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
    # "5 cardboard pallet" typed Marking summary (SOE 2nd, 1267475174)
    hits = list(_PKG_SUMMARY_TYPED.finditer(text))
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


def _parse_items(
    text: str,
    invoice_no: str | None,
    currency: str | None,
    pn_pairs: list[tuple[str, str, str]] | None = None,
) -> list[Item]:
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
        if origin is None:
            # Bare country line (no per-line Net weight printed) before HS.
            head = window.split("Customs", 1)[0]
            bm = _ORIGIN_BARE.search(head)
            if bm and bm.group("origin") not in ("PC", "KG"):
                origin = bm.group("origin")
        hm = _HS.search(window)
        hs = hm.group("hs") if hm else None
        try:
            qty = us_float(m.group("qty"))
            price = us_float(m.group("price"))
            amt = us_float(m.group("amt"))
        except ValueError:
            continue
        unit_price = price / price_unit if price_unit else price
        if pn_pairs is not None:
            pn_pairs.append((m.group("item"), m.group("pn"), m.group("cust")))
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


def _pn_reading_conflicts(text: str, pn_pairs: list[tuple[str, str, str]]) -> list[str]:
    """OCR only: every reading of the same 10-digit Bosch PN stem anywhere in
    the scan (item row, Customer PN column, cargo list, delivery note,
    marking) must carry the same 3-char suffix. Disagreement (e.g. 57G / 576 /
    876) means the OCR cannot be trusted for that PN."""
    out = []
    seen: set[str] = set()
    for item_no, pn, _cust in pn_pairs:
        digits = re.sub(r"[^0-9]", "", pn.split("-", 1)[0])
        if len(digits) != 10 or digits in seen:
            continue
        seen.add(digits)
        rx = re.compile(
            rf"(?<![0-9]){digits[:4]}[ .,]*{digits[4:7]}[ .,]*{digits[7:]}[ \-]*"
            r"(?P<suf>[A-Za-z0-9]{3})"
        )
        sufs = [m.group("suf").upper() for m in rx.finditer(text)]
        uniq = list(dict.fromkeys(sufs))
        if len(uniq) > 1:
            readings = ", ".join(f"-{u}×{sufs.count(u)}" for u in uniq)
            out.append(f"line {item_no} {pn}: suffix readings {readings}")
    return out


_PAGE_MARK = re.compile(
    r"Invoice(?:\s+Copy|\s+and\s+Packing\s+List)?\s+(?P<i>\d{1,2})\s*/\s*(?P<n>\d{1,2})\b",
    re.I,
)


def _missing_pages_note(text: str) -> str | None:
    """Soft: printed page marks "k / M" but some k in 1..M absent from the PDF."""
    marks = [(int(m.group("i")), int(m.group("n"))) for m in _PAGE_MARK.finditer(text)]
    if not marks:
        return None
    total = max(n for _, n in marks)
    have = {i for i, n in marks if n == total}
    missing = [k for k in range(1, total + 1) if k not in have]
    if not missing or total > 30:
        return None
    return (
        "SOFT: invoice page(s) "
        + ", ".join(f"{k}/{total}" for k in missing)
        + " not in PDF (fields printed only there, e.g. Marking/pallets, stay empty)"
    )


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> ExtractResult:
    from invoice_extractor.ocr import is_ocr_backend

    notes: list[str] = []
    gold_fields: list[str] = []
    ocr = is_ocr_backend(backend)
    if ocr:
        text, misread = normalize_ocr_partnumbers(text)
        if misread:
            gold_fields.append("items.part_no")
            notes.append(
                "NEEDS_GOLD: OCR misread part no. separators ("
                + ", ".join(dict.fromkeys(misread))
                + "); PN characters unreliable (e.g. G/6), confirm on PDF"
            )

    miss = _missing_pages_note(text)
    if miss:
        notes.append(miss)

    inv = _invoice_no(text)
    amount, currency = _amount_currency(text)
    pn_pairs: list[tuple[str, str, str]] = []
    items = _parse_items(text, inv, currency, pn_pairs)
    if ocr:
        bad = _pn_reading_conflicts(text, pn_pairs)
        if bad:
            if "items.part_no" not in gold_fields:
                gold_fields.append("items.part_no")
            notes.append(
                "NEEDS_GOLD: OCR readings of the same part no. disagree in this scan ("
                + "; ".join(bad)
                + "); item-row value kept as read, confirm on PDF"
            )
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

    res = ExtractResult(
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
            notes=("; ".join(notes) if notes else None) if items else NOTES,
            needs_gold=bool(gold_fields),
            needs_gold_fields=gold_fields or None,
        ),
    )
    if gold_fields:
        res.meta.confidence = "needs_gold"
    return res
