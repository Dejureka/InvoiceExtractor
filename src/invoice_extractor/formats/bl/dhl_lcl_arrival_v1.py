"""DHL Global Forwarding Taiwan — 海運 LCL 到貨通知 layout family.

Case 2: ``到貨通知 - NGOA23259.pdf``.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta, loose_date_to_iso

MATCH_HINTS = {
    "filename_regex": r"到貨通知|NGOA|ARN",
    "keywords": [
        "海運 LCL 到貨通知",
        "DHL GLOBAL FORWARDING",
        "HBL 提單號碼",
        "SHIPMENT",
        "CONSOL",
    ],
}

NOTES = (
    "DHL GF Taiwan LCL arrival notice. Samples: 到貨通知 - NGOA23259.pdf (BHC case2)."
)

RULES_JSON = {
    "id": "dhl_lcl_arrival_v1",
    "doc_kind": "arrival_notice",
    "header": {
        "hbl_no": r"HBL 提單號碼\s+(\S+)",
        "mbl_no": r"MASTER BILL OF LADING.*?([A-Z]{4,}[A-Z0-9]{8,})",
        "eta": r"(\d{4}-\d{2}-\d{2})",
        "packages": r"(\d+)\s+CAS",
        "gross_weight_kg": r"(\d+(?:\.\d+)?)\s+KG",
        "invoice_refs": r"INVOICE NO\.?\s*([A-Z0-9\-]+)",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    tu = text.upper()
    if "到貨通知" in filename or "NGOA" in filename.upper():
        score += 0.15
    if "海運 LCL 到貨通知" in text:
        score += 0.4
    if "DHL GLOBAL FORWARDING" in text or "敦豪全球貨運" in text:
        score += 0.25
    if "HBL 提單號碼" in text:
        score += 0.2
    if "CEVA LOGISTICS" in text or "PYRAMID LINES" in text:
        score -= 0.6
    if "HIPPOPO" in tu:
        score -= 0.3
    # Danmar / Japan ocean B/L draft is a different family
    if "DANMAR LINES" in tu or "DHL GLOBAL FORWARDING JAPAN" in tu:
        score -= 0.8
    if "BILL OF LADING" in tu and "海運 LCL 到貨通知" not in text:
        score -= 0.4
    if "海運 LCL 到貨通知" not in text and "HBL 提單號碼" not in text:
        score = min(score, 0.25)
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def _split_two_col(line: str) -> tuple[str, str | None]:
    """Split a layout line on a wide horizontal gap (2+ spaces)."""
    parts = re.split(r"[^\S\n]{2,}", line.strip())
    parts = [p for p in parts if p]
    if len(parts) >= 2:
        return parts[0], parts[1]
    return (parts[0] if parts else ""), None


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="DHL Global Forwarding (Taiwan)", load_type="LCL")

    m = re.search(r"HBL 提單號碼\s+(\S+)", text)
    if m:
        h.hbl_no = m.group(1).strip()
        h.bl_no = h.hbl_no

    # MBL sits under MASTER BILL OF LADING (right column), e.g. NGOKEL260806173
    m = re.search(
        r"MASTER BILL OF LADING\s*\n[^\n]*?[^\S\n]{2,}([A-Z0-9]{10,})",
        text,
    )
    if not m:
        m = re.search(r"\b(NGOKEL\d+|NGO[A-Z0-9]{8,})\b", text)
    if m:
        h.mbl_no = m.group(1).strip()

    # Shipper / Consignee: two-column header then first data row
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if re.search(r"SHIPPER.*CONSIGNEE", ln):
            if i + 1 < len(lines):
                left, right = _split_two_col(lines[i + 1])
                h.shipper = _snip(left)
                h.consignee = _snip(right)
            break

    m = re.search(r"INVOICE NO\.?\s*([A-Z0-9\-]+)", text, re.I)
    if m:
        h.invoice_refs = m.group(1).strip()

    # Page2 totals: 5 CAS … 3560.000 KG … 4.470 M3
    m = re.search(
        r"(\d+)\s+CAS\s*\([^)]*\)[^\n]*?([\d.]+)\s+KG[^\n]*?([\d.]+)\s+M3",
        text,
    )
    if m:
        h.packages = float(m.group(1))
        h.package_unit = "CAS"
        h.gross_weight_kg = us_float(m.group(2))
        h.measurement_cbm = us_float(m.group(3))
    else:
        m = re.search(r"(\d+)\s+CASES?", text, re.I)
        if m:
            h.packages = float(m.group(1))
            h.package_unit = "CASES"
        m = re.search(r"([\d.]+)\s+KG\b", text)
        if m and h.gross_weight_kg is None:
            h.gross_weight_kg = us_float(m.group(1))

    m = re.search(r"SEA\s+([A-Z0-9][A-Z0-9 \-]+?)\s*/\s*(\S+)\s*/", text)
    if m:
        h.vessel = m.group(1).strip()
        h.voyage = m.group(2).strip()

    m = re.search(
        r"(\d{4}-\d{2}-\d{2})\s+(\d{4}-\d{2}-\d{2})\s*\n",
        text,
    )
    if m:
        h.etd = loose_date_to_iso(m.group(1))
        h.eta = loose_date_to_iso(m.group(2))
    else:
        dates = re.findall(r"(\d{4}-\d{1,2}-\d{1,2})", text)
        if len(dates) >= 2:
            h.etd = loose_date_to_iso(dates[-2])
            h.eta = loose_date_to_iso(dates[-1])

    m = re.search(r"(JPNGO)\s*=\s*([^,\n]+)", text)
    if m:
        h.pol = _snip(f"{m.group(1)} = {m.group(2).strip()}", 60)
    m = re.search(r"(TWKEL)\s*=\s*([^,\n]+)", text)
    if m:
        h.pod = _snip(f"{m.group(1)} = {m.group(2).strip()}", 60)

    m = re.search(r"貨櫃號碼[^\n]*\n([A-Z]{4}\d{7})", text)
    if m:
        h.container_nos = m.group(1)

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="dhl_lcl_arrival_v1",
            confidence="rules",
            needs_ocr=needs_ocr,
            doc_kind="arrival_notice",
        ),
    )
