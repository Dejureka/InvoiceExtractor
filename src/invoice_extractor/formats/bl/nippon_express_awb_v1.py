"""Nippon Express (M) air waybill — MA 50-N pdfdq_p01_nem… family.

Samples: ``pdfdq_p01_nem17159645_….pdf``, ``pdfdq_p01_nem17164630_….pdf``.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta, loose_date_to_iso

MATCH_HINTS = {
    "filename_regex": r"pdfdq_p01_nem|nem\d{10}",
    "keywords": [
        "AIR WAYBILL",
        "NIPPON EXPRESS",
        "AIR WAYBILL NUMBER",
        "NEM ",
        "Airport of Destination",
    ],
}

NOTES = (
    "Nippon Express (M) SDN. BHD. air waybill (MA 50-N pdfdq_p01_nem…). "
    "HAWB NEM #### ####; packages = No. of Pieces RCP; GW from Gross Weight K."
)

RULES_JSON = {
    "id": "nippon_express_awb_v1",
    "doc_kind": "air_waybill",
    "header": {
        "bl_no": r"NEM\s*([\d\s]{8,})",
        "packages": r"^\s*(\d+)\s+([\d.]+)\s*K\b",
        "gross_weight_kg": r"([\d.]+)\s*K\s*Q",
        "invoice_refs": r"INV\s*NO\.?\s*(AK\d+)",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename.lower()
    if "pdfdq" in fn or re.search(r"nem\d{8,}", fn):
        score += 0.3
    if "AIR WAYBILL" in text or "AIR CONSIGNMENT NOTE" in text:
        score += 0.3
    if "NIPPON EXPRESS" in text:
        score += 0.3
    if re.search(r"\bNEM\s*\d{4}", text):
        score += 0.2
    if "ARRIVAL NOTICE" in text or "到貨通知" in text or "MILESTONE" in text:
        score -= 0.5
    if "CEVA LOGISTICS" in text or "DHL GLOBAL FORWARDING" in text:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="Nippon Express (M) SDN. BHD.", load_type="AIR")

    # HAWB: NEM 1715 9645 → NEM17159645
    m = re.search(r"\bNEM\s*(\d{4})\s*(\d{4})\b", text)
    if m:
        hawb = f"NEM{m.group(1)}{m.group(2)}"
        h.bl_no = hawb
        h.hbl_no = hawb
    else:
        m = re.search(r"\bNEM\s*([\d\s]{8,14})", text)
        if m:
            hawb = "NEM" + re.sub(r"\D", "", m.group(1))
            h.bl_no = hawb
            h.hbl_no = hawb

    # MAWB: 843 - 4620 8680
    m = re.search(r"\b(\d{3})\s*-\s*([\d\s]{6,12})", text)
    if m:
        h.mbl_no = m.group(1) + "-" + re.sub(r"\s+", "", m.group(2))

    # Pieces + GW: "3          279.0 K Q"
    m = re.search(
        r"(?m)^\s*(\d+)\s+([\d.]+)\s*K\s*Q\b",
        text,
    )
    if m:
        h.packages = float(m.group(1))
        h.package_unit = "PIECES"
        h.gross_weight_kg = us_float(m.group(2))
    else:
        m = re.search(r"(?m)^\s*(\d+)\s+([\d.]+)\s*K\b", text)
        if m:
            h.packages = float(m.group(1))
            h.package_unit = "PIECES"
            h.gross_weight_kg = us_float(m.group(2))

    # CBM from "2.057 M3"
    m = re.search(r"([\d.]+)\s*M3\b", text)
    if m:
        h.measurement_cbm = us_float(m.group(1))

    m = re.search(r"INV\s*NO\.?\s*(AK\d+)", text, re.I)
    if m:
        h.invoice_refs = m.group(1).upper()

    m = re.search(r"Airport of Departure[^\n]*\n\s*([A-Z][A-Z ]+?)\s{2,}", text)
    if m:
        h.pol = _snip(m.group(1).strip())
    if not h.pol and "KUALA LUMPUR" in text:
        h.pol = "KUALA LUMPUR"

    m = re.search(r"Airport of Destination\s*\n\s*([A-Z][A-Z0-9 ]+)", text)
    if m:
        h.pod = _snip(m.group(1).strip())
    if not h.pod and "TAOYUAN" in text:
        h.pod = "TAOYUAN AIRPORT"

    # Flight: D7 378 /10
    m = re.search(r"\b([A-Z0-9]{2}\s*\d{2,4})\s*/\s*(\d{1,2})\b", text)
    if m:
        h.voyage = re.sub(r"\s+", " ", m.group(1)).strip() + "/" + m.group(2)

    # Shipper / Consignee blocks (simple)
    m = re.search(r"ROBERT BOSCH SDN BHD", text)
    if m:
        h.shipper = "ROBERT BOSCH SDN BHD"
    m = re.search(r"ROBERT BOSCH TAIWAN", text, re.I)
    if m:
        h.consignee = "ROBERT BOSCH TAIWAN CO.,LTD."

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="nippon_express_awb_v1",
            confidence="rules",
            needs_ocr=needs_ocr,
            doc_kind="air_waybill",
        ),
    )
