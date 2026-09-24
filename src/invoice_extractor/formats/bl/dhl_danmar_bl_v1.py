"""DHL Global Forwarding / Danmar Lines — ocean B/L draft v1.

BHC 3rd case2: ``Bill Of Lading - NGOA23906.pdf`` (Marubeni copper tube).
Distinct from ``dhl_lcl_arrival_v1`` (Taiwan 海運 LCL 到貨通知).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta

MATCH_HINTS = {
    "filename_regex": r"Bill Of Lading|NGOA|Danmar|B\.L\.\s*No",
    "keywords": [
        "Danmar Lines",
        "DHL GLOBAL FORWARDING JAPAN",
        "B.L. No.",
        "Express Sea Waybill",
    ],
}

NOTES = (
    "DHL GF Japan / Danmar Lines ocean B/L draft (NGOA…). "
    "Sample: Bill Of Lading - NGOA23906.pdf (BHC 3rd case2)."
)

RULES_JSON = {
    "id": "dhl_danmar_bl_v1",
    "doc_kind": "bl",
    "header": {
        "bl_no": r"B\.L\.\s*No\.?\s*(NGOA\w+)",
        "packages": r"(\d+)\s+Case\(s\)|Total No\..*?(\d+)\s+CASE",
        "gross_weight_kg": r"([\d,]+\.\d{3})\s*KG",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    tu = text.upper()
    if "BILL OF LADING" in fn or "NGOA" in fn or "DANMAR" in fn:
        score += 0.25
    if "DANMAR LINES" in tu:
        score += 0.4
    if "DHL GLOBAL FORWARDING JAPAN" in tu or "DHL GLOBAL FORWARDING SG" in tu:
        score += 0.25
    if re.search(r"B\.L\.\s*No", text, re.I) or re.search(r"\bNGOA\w+", tu):
        score += 0.2
    if "海運 LCL 到貨通知" in text:
        score -= 0.8
    if "ARRIVAL NOTICE" in tu or "到貨通知" in text:
        score -= 0.6
    if "HIPPOPO" in tu or "CEVA LOGISTICS" in tu:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="DHL Global Forwarding / Danmar Lines")

    m = re.search(r"B\.L\.\s*No\.?\s*(NGOA\w+)", text, re.I)
    if not m:
        m = re.search(r"\b(NGOA\w+)\b", text, re.I)
    if m:
        h.bl_no = m.group(1).upper()
        h.hbl_no = h.bl_no

    m = re.search(r"Shipper\s*\n\s*([A-Z][^\n]{5,80})", text, re.I)
    if m:
        h.shipper = _snip(m.group(1))

    m = re.search(r"Consignee[^\n]*\n\s*([A-Z][^\n]{5,80})", text, re.I)
    if m:
        h.consignee = _snip(m.group(1))

    m = re.search(r"Vessel\s+Voyage No\.\s*\n\s*([A-Z0-9 ]+?)\s+(\d+\w*)", text, re.I)
    if not m:
        # Layout: Vessel line then name/voyage in columns
        m = re.search(r"\b(TS\s+[A-Z]+)\s+(\d+\w*)\b", text)
    if m:
        h.vessel = re.sub(r"\s+", " ", m.group(1)).strip()
        h.voyage = m.group(2)

    if re.search(r"NAGOYA", text, re.I):
        h.pol = "NAGOYA, JAPAN"
    if re.search(r"KEELUNG", text, re.I):
        h.pod = "KEELUNG, TAIWAN"

    m = re.search(r"(\d+)\s+Case\(s\)", text, re.I)
    if not m:
        m = re.search(r"Total No\.\s*of containers/packages:\s*(\d+)\s+CASE", text, re.I)
    if m:
        h.packages = float(m.group(1))
        h.package_unit = "CASE"

    m = re.search(r"([\d,]+\.\d{3})\s*KG", text, re.I)
    if m:
        h.gross_weight_kg = us_float(m.group(1))

    refs = []
    for mm in re.finditer(r"INVOICE\s+NO\.?\s*(JCH[\w-]+)", text, re.I):
        refs.append(mm.group(1).upper())
    if refs:
        h.invoice_refs = ", ".join(dict.fromkeys(refs))

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
            format_id="dhl_danmar_bl_v1",
            confidence=conf,
            needs_ocr=needs_ocr,
            needs_gold=needs_gold,
            doc_kind="bl",
            notes=NOTES if conf == "rules" else "Danmar BL partial",
        ),
    )
