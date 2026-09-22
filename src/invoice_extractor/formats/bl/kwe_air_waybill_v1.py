"""Kintetsu World Express (KWE) IATA air waybill — SOE HAWB/HAWC family.

Sample: ``122019555195-HAWC.pdf`` (MAWB 1220-19555195).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta, loose_date_to_iso

MATCH_HINTS = {
    "filename_regex": r"HAW[BC]|1220\d{8}|KWE",
    "keywords": [
        "KINTETSU WORLD EXPRESS",
        "Air Waybill",
        "Shipper's Name and Address",
        "No.of",
        "Pieces",
        "Gross",
        "Weight",
    ],
}

NOTES = (
    "KWE / Kintetsu World Express air waybill (SOE 50-KWE HAWC). "
    "HAWB = 1220-######## from face; packages = No.of Pieces RCP; "
    "GW from Gross Weight … K. Invoice ref INV NO.########."
)

RULES_JSON = {
    "id": "kwe_air_waybill_v1",
    "doc_kind": "air_waybill",
    "header": {
        "bl_no": r"\b(1220[-\s]?\d{8})\b",
        "packages": r"(?m)^\s*(\d+)\s+([\d.]+)\s*K\b",
        "gross_weight_kg": r"([\d.]+)\s*K\b",
        "invoice_refs": r"INV\s*NO\.?\s*(\d{8,12})",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.upper()
    if "HAWC" in fn or "HAWB" in fn or re.search(r"1220\d{8}", fn):
        score += 0.3
    if "KINTETSU WORLD EXPRESS" in text:
        score += 0.45
    if "Air Waybill" in text or "AIR WAYBILL" in text:
        score += 0.2
    if re.search(r"\b1220[-\s]?\d{8}\b", text):
        score += 0.15
    if "NIPPON EXPRESS" in text or re.search(r"\bNEM\s*\d{4}", text):
        score -= 0.5
    if "MAERSK LOGISTICS" in text:
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
    h = BLHeader(forwarder="Kintetsu World Express, Inc.", load_type="AIR")

    # Prefer dashed form 1220-19555195
    m = re.search(r"\b(1220)\s*[- ]?\s*(\d{8})\b", text)
    if m:
        hawb = f"{m.group(1)}-{m.group(2)}"
        h.bl_no = hawb
        h.hbl_no = hawb
        h.mbl_no = hawb
    else:
        m = re.search(r"\b(1220\d{8})\b", text)
        if m:
            raw = m.group(1)
            hawb = f"{raw[:4]}-{raw[4:]}"
            h.bl_no = hawb
            h.hbl_no = hawb
            h.mbl_no = hawb

    # Pieces + GW: "1              496.0 K"
    m = re.search(
        r"(?m)^\s*(\d+)\s+([\d.]+)\s*K(?:\s|$)",
        text,
    )
    if m:
        h.packages = float(m.group(1))
        h.package_unit = "PIECES"
        h.gross_weight_kg = us_float(m.group(2))

    m = re.search(r"INV\s*NO\.?\s*(\d{8,12})", text, re.I)
    if m:
        h.invoice_refs = m.group(1)

    if "NARITA" in text:
        h.pol = "NARITA"
    m = re.search(r"Airport of Destination[^\n]*\n\s*([A-Z][A-Z ]+)", text)
    if m:
        h.pod = _snip(m.group(1))
    if not h.pod and "KAOHSIUNG" in text:
        h.pod = "KAOHSIUNG"

    m = re.search(r"\b([A-Z]{2}\d{2,4}/\d{1,2})\b", text)
    if m:
        h.voyage = m.group(1)

    m = re.search(r"(\d{1,2}/[A-Z]{3}/\d{4})", text)
    if m:
        h.eta = loose_date_to_iso(m.group(1))
    else:
        m = re.search(r"Executed on \(date\)[^\n]*\n[^\n]*?(\d{1,2}/[A-Z]{3}/\d{4})", text)
        # date may be on same area: 19/SEP/2026
        m = re.search(r"\b(\d{1,2}/[A-Z]{3}/\d{4})\b", text)
        if m:
            h.eta = loose_date_to_iso(m.group(1))

    if "BOSCH CORPORATION" in text:
        h.shipper = "BOSCH CORPORATION"
    if re.search(r"ROBERT BOSCH TAIWAN", text, re.I):
        h.consignee = "ROBERT BOSCH TAIWAN CO., LTD."

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="kwe_air_waybill_v1",
            confidence="rules",
            needs_ocr=needs_ocr,
            doc_kind="air_waybill",
        ),
    )
