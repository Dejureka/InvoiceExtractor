"""Maersk Logistics & Services Germany — IATA air waybill (SOE HAWB QU…).

Sample: ``Copy 7 - (Extra Copy) - HAWB No_ QU100002136.pdf``.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta, loose_date_to_iso

MATCH_HINTS = {
    "filename_regex": r"HAWB|QU\d{8,}",
    "keywords": [
        "MAERSK LOGISTICS",
        "HAWB No",
        "Air Waybill",
        "Shipper's Name and Address",
        "No. Of",
        "Pieces",
    ],
}

NOTES = (
    "Maersk Logistics & Services Germany A/S air waybill (SOE HAWB QU########). "
    "packages = No. Of Pieces RCP; GW from Gross Weight … K Q; "
    "Invoice No. on face when present."
)

RULES_JSON = {
    "id": "maersk_air_waybill_v1",
    "doc_kind": "air_waybill",
    "header": {
        "bl_no": r"HAWB\s*No\s*:?\s*(QU\d{8,})",
        "packages": r"(?m)^\s*(\d+)\s+([\d.]+)\s*K\s*Q\b",
        "gross_weight_kg": r"([\d.]+)\s*K\s*Q\b",
        "invoice_refs": r"Invoice\s*No\.?\s*:?\s*(\d{8,12})",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "HAWB" in fn or re.search(r"QU\d{8,}", fn):
        score += 0.3
    if "MAERSK LOGISTICS" in text:
        score += 0.45
    if re.search(r"HAWB\s*No\s*:?\s*QU\d+", text, re.I):
        score += 0.25
    if "Air Waybill" in text or "AIR WAYBILL" in text:
        score += 0.1
    if "KINTETSU WORLD EXPRESS" in text:
        score -= 0.5
    if "NIPPON EXPRESS" in text:
        score -= 0.4
    if "ARRIVAL NOTICE" in text or "到貨通知" in text:
        score -= 0.5
    if "Bosch Partnumber" in text and "Invoice amount" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(
        forwarder="Maersk Logistics & Services Germany A/S & Co. KG",
        load_type="AIR",
    )

    m = re.search(r"HAWB\s*No\s*:?\s*(QU\d{8,})", text, re.I)
    if m:
        hawb = m.group(1).upper()
        h.bl_no = hawb
        h.hbl_no = hawb
    else:
        m = re.search(r"\b(QU\d{8,})\b", text)
        if m:
            hawb = m.group(1).upper()
            h.bl_no = hawb
            h.hbl_no = hawb

    # "2                      294.5 K Q"
    m = re.search(r"(?m)^\s*(\d+)\s+([\d.]+)\s*K\s*Q\b", text)
    if m:
        h.packages = float(m.group(1))
        h.package_unit = "PIECES"
        h.gross_weight_kg = us_float(m.group(2))
    else:
        m = re.search(r"(?m)^\s*(\d+)\s+([\d.]+)\s*$", text)
        # weaker fallback near pieces block
        m2 = re.search(r"(?m)^(\d+)\s+([\d.]+)\s*$", text)
        if m2 and float(m2.group(1)) < 100:
            h.packages = float(m2.group(1))
            h.package_unit = "PIECES"
            h.gross_weight_kg = us_float(m2.group(2))

    m = re.search(r"Invoice\s*No\.?\s*:?\s*(\d{8,12})", text, re.I)
    if m:
        h.invoice_refs = m.group(1)

    m = re.search(r"VOL\s*([\d.]+)\s*M3", text, re.I)
    if m:
        h.measurement_cbm = us_float(m.group(1))

    if "FRANKFURT" in text:
        h.pol = "FRANKFURT AM MAIN"
    if "KAOHSIUNG" in text:
        h.pod = "KAOHSIUNG"

    m = re.search(r"\b([A-Z]{2}\d{2,4}/\d{2})\b", text)
    if m:
        h.voyage = m.group(1)

    m = re.search(r"\b(\d{2}-[A-Za-z]{3}-\d{2})\b", text)
    if m:
        h.eta = loose_date_to_iso(m.group(1))

    if "ROBERT BOSCH GMBH" in text:
        h.shipper = "ROBERT BOSCH GMBH"
    if re.search(r"ROBERT BOSCH TAIWAN", text, re.I):
        h.consignee = "ROBERT BOSCH TAIWAN CO., LTD."

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="maersk_air_waybill_v1",
            confidence="rules",
            needs_ocr=needs_ocr,
            doc_kind="air_waybill",
        ),
    )
