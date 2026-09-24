"""Shenzhen China Progress International — ocean B/L v1.

BHC 3rd case5: ``44266提单.pdf`` (Dunan / NBSE…). Delivery agent often Hippopo.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta, loose_date_to_iso

MATCH_HINTS = {
    "filename_regex": r"提单|NBSE|44266|Progress",
    "keywords": [
        "CHINA PROGRESS INTERNATIONAL",
        "中进国际",
        "B/L NUMBER",
        "NBSE",
    ],
}

NOTES = (
    "China Progress International ocean B/L (NBSE…). "
    "Sample: 44266提单.pdf (BHC 3rd case5 Dunan)."
)

RULES_JSON = {
    "id": "china_progress_bl_v1",
    "doc_kind": "bl",
    "header": {
        "bl_no": r"B/L\s+NUMBER\s+(NBSE\w+)",
        "packages": r"(\d+)\s*PALLETS",
        "gross_weight_kg": r"([\d,]+\.\d{3})\s*KGS",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename
    tu = text.upper()
    if "提单" in fn or "NBSE" in fn.upper() or "PROGRESS" in fn.upper():
        score += 0.25
    if "CHINA PROGRESS" in tu or "中进国际" in text:
        score += 0.5
    if re.search(r"\bNBSE\w+", tu):
        score += 0.25
    if "B/L NUMBER" in tu:
        score += 0.1
    if "ARRIVAL NOTICE" in tu or "到貨通知書" in text:
        score -= 0.6
    if "DANMAR" in tu:
        score -= 0.5
    if "T.V.L" in tu or "TRANS VAN LINKS" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="Shenzhen China Progress International Forwarding")

    m = re.search(r"B/L\s+NUMBER\s+(NBSE\w+)", text, re.I)
    if not m:
        m = re.search(r"\b(NBSE\w+)\b", text, re.I)
    if m:
        h.bl_no = m.group(1).upper()
        h.hbl_no = h.bl_no

    m = re.search(r"SHIPPER/EXPORTER\s*\n\s*([A-Z][^\n]{5,80})", text, re.I)
    if m:
        h.shipper = _snip(m.group(1))

    m = re.search(r"CONSIGNEE:\s*\n\s*([A-Z][^\n]{5,80})", text, re.I)
    if m:
        h.consignee = _snip(m.group(1))

    m = re.search(
        r"OCEAN VESSEL/\s*VOYAGE NO\.\s+PORT OF LOADING\s*\n\s*([A-Z0-9 ]+?)\s+(\d+\w*)\s+([A-Z][^\n,]*)",
        text,
        re.I,
    )
    if m:
        h.vessel = re.sub(r"\s+", " ", m.group(1)).strip()
        h.voyage = m.group(2)
        h.pol = _snip(m.group(3))
    if re.search(r"KEELUNG", text, re.I):
        h.pod = "KEELUNG"

    m = re.search(r"DATE OF ISSUE\s+([A-Z]{3}\.?\d{0,2},?\s*\d{4}|[\d/]+)", text, re.I)
    # skip

    m = re.search(r"(\d+)\s*PALLETS", text, re.I)
    if m:
        h.packages = float(m.group(1))
        h.package_unit = "PALLETS"

    m = re.search(r"([\d,]+\.\d{3})\s*KGS", text, re.I)
    if m:
        h.gross_weight_kg = us_float(m.group(1))

    conf = "rules"
    needs_gold = False
    if not h.bl_no:
        conf = "needs_gold"
        needs_gold = True

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="china_progress_bl_v1",
            confidence=conf,
            needs_ocr=needs_ocr,
            needs_gold=needs_gold,
            doc_kind="bl",
            notes=NOTES if conf == "rules" else "China Progress BL partial",
        ),
    )
