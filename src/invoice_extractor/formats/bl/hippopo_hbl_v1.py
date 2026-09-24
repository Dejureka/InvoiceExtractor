"""Hippopo Global Logistics HBL draft — shared sparse HBL layout family.

Case 3: ``HBL draft HB26090012 KTMBE26080067.pdf``.
Shipper on face (AICHI); notify/agent Hippopo; HBL no top-right.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta, loose_date_to_iso

MATCH_HINTS = {
    "filename_regex": r"HBL|HB\d{8}",
    "keywords": [
        "HIPPOPO GLOBAL LOGISTICS",
        "COMMERCIAL INVOICE",
        "FREIGHT COLLECT",
        "PALLETS",
    ],
}

NOTES = (
    "Hippopo HBL draft (sparse bill face). Sample: HBL draft HB26090012….pdf (BHC case3)."
)

RULES_JSON = {
    "id": "hippopo_hbl_v1",
    "doc_kind": "hbl",
    "header": {
        "hbl_no": r"\b(HB\d{8})\b",
        "packages": r"(\d+)\s+PALLETS?",
        "gross_weight_kg": r"([\d,]+\.?\d*)\s+KGS",
        "invoice_refs": r"NUMBERS?\s+(AETW\d+)",
        "vessel": r"(YM\s+\w+)\s+V\.?\s*(\S+)",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if "HBL" in fn or re.search(r"HB\d{8}", fn):
        score += 0.3
    if "HIPPOPO" in tu:
        score += 0.35
    if re.search(r"\bHB\d{8}\b", text):
        score += 0.3
    if "FREIGHT COLLECT" in text:
        score += 0.05
    # This module is HBL *draft* face (HB########), not arrival notice / third-party B/L
    if "ARRIVAL NOTICE" in tu or "到貨通知書" in text or "到貨通知" in text:
        score -= 0.7
    if "CEVA LOGISTICS" in text:
        score -= 0.5
    if "MILESTONE FORWARDING" in text or "里運國際" in text:
        score -= 0.6
    if "DHL GLOBAL FORWARDING" in text:
        score -= 0.5
    if "CHINA PROGRESS" in tu or "中进国际" in text:
        score -= 0.8
    if "B/L NUMBER" in tu and not re.search(r"\bHB\d{8}\b", text):
        score -= 0.4
    if "INVOICE" in text and "HIPPOPO" not in tu and "HBL" not in fn:
        score -= 0.2
    # Require HB######## style id for a confident match
    if not re.search(r"\bHB\d{8}\b", text) and "HBL" not in fn:
        score = min(score, 0.25)
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="Hippopo Global Logistics")

    m = re.search(r"\b(HB\d{8})\b", text)
    if m:
        h.hbl_no = m.group(1)
        h.bl_no = m.group(1)

    # First non-empty block ≈ shipper
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    # Skip HBL number-only first line if present
    start = 0
    if lines and re.fullmatch(r"HB\d{8}", lines[0]):
        start = 1
    if start < len(lines):
        h.shipper = _snip(lines[start])
    # Consignee often after shipper address block — look for BOSCH
    for ln in lines:
        if "BOSCH" in ln.upper() and "CO" in ln.upper():
            h.consignee = _snip(ln)
            break

    m = re.search(r"(\d+)\s+PALLETS?", text, re.I)
    if m:
        h.packages = float(m.group(1))
        h.package_unit = "PALLETS"

    m = re.search(r"([\d,]+\.?\d*)\s+KGS\s+([\d.]+)\s+CBM", text, re.I)
    if m:
        h.gross_weight_kg = us_float(m.group(1))
        h.measurement_cbm = us_float(m.group(2))
    else:
        m = re.search(r"([\d,]+\.?\d*)\s+KGS", text, re.I)
        if m:
            h.gross_weight_kg = us_float(m.group(1))

    m = re.search(r"NUMBERS?\s+(AETW\d+)", text, re.I)
    if m:
        h.invoice_refs = m.group(1)
    else:
        m = re.search(r"\b(AETW\d+)\b", text)
        if m:
            h.invoice_refs = m.group(1)

    # Vessel / voyage: "YM INAUGURATION 343S" or "YM INAUGURATION V.343S"
    m = re.search(r"(YM\s+[A-Z]+)\s+V\.?\s*([A-Z0-9]+)", text)
    if m:
        h.vessel = m.group(1).strip()
        h.voyage = m.group(2).strip()
    else:
        m = re.search(r"(YM\s+[A-Z]+)\s+(\d{3}[A-Z]?)\b", text)
        if m:
            h.vessel = m.group(1).strip()
            h.voyage = m.group(2).strip()

    # Ports: NAGOYA … KEELUNG
    if re.search(r"NAGOYA", text, re.I):
        h.pol = "NAGOYA, JAPAN"
    if re.search(r"KEELUNG", text, re.I):
        h.pod = "KEELUNG, TAIWAN"

    m = re.search(r"([A-Z]{4}\d{7})", text)
    if m:
        h.container_nos = m.group(1)

    # Date near bottom TOKYO 2026-09-03
    m = re.search(r"TOKYO\s+(\d{4}-\d{2}-\d{2})", text)
    if m:
        # issue date — not ETA; leave eta None unless voyage date doubles
        pass
    m = re.search(r"V\.\d+\S*\s+(\d{4}-\d{2}-\d{2})", text)
    if m:
        h.etd = loose_date_to_iso(m.group(1))

    # 20GP → FCL-ish
    if re.search(r"\b20GP\b|\b40(?:HC|GP)\b", text):
        h.load_type = "FCL"

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="hippopo_hbl_v1",
            confidence="rules",
            needs_ocr=needs_ocr,
            doc_kind="hbl",
        ),
    )
