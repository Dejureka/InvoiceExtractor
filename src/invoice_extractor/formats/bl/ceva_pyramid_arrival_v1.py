"""CEVA / Pyramid Lines Taiwan arrival notice (到貨通知) — shared layout family.

Cases 4/5/6: ``到貨 448.pdf``, ``到貨 449.pdf``, ``到貨 298.pdf``.
Agent: 捷飛運通 / CEVA LOGISTICS (TAIWAN) for Pyramid Lines Singapore.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta, loose_date_to_iso

MATCH_HINTS = {
    "filename_regex": r"到貨|arrival|WEB\d+",
    "keywords": [
        "到貨通知",
        "CEVA LOGISTICS",
        "PYRAMID LINES",
        "捷飛運通",
        "B/L no",
    ],
}

NOTES = (
    "CEVA/Pyramid Taiwan arrival notice (到貨通知). Shared layout for WEB* HBLs. "
    "Samples: 到貨 448/449/298.pdf (BHC cases 4/5/6)."
)

RULES_JSON = {
    "id": "ceva_pyramid_arrival_v1",
    "doc_kind": "arrival_notice",
    "header": {
        "bl_no": r"B/L no\s*:\s*(\S+)",
        "vessel": r"VESSEL\s*:\s*(.+?)\s+VOYAGE",
        "voyage": r"VOYAGE\.\s*(\S+)",
        "eta": r"ETA\s*:\s*([\d/]+)",
        "packages": r"Packings\s*:\s*([\d.]+)",
        "gross_weight_kg": r"G\.W\.:\s*([\d.]+)",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    fn = filename
    tu = text.upper()
    if "到貨" in fn or re.search(r"WEB\d{9}", fn, re.I):
        score += 0.15
    if "到貨通知" in text:
        score += 0.1
    if "CEVA LOGISTICS" in text or "捷飛運通" in text:
        score += 0.4
    if "PYRAMID LINES" in text:
        score += 0.25
    if re.search(r"B/L no\s*:", text):
        score += 0.15
    if "海運 LCL 到貨通知" in text or "DHL GLOBAL FORWARDING" in text:
        score -= 0.6
    if "BILL OF LADING" in tu and "CEVA" not in tu:
        score -= 0.2
    # Hippopo / Milestone arrival notices share 到貨通知 filename — do not steal
    if "HIPPOPO" in tu or "河馬" in text:
        score -= 0.8
    if "MILESTONE FORWARDING" in tu or "里運國際" in text:
        score -= 0.8
    # Require at least one CEVA-family anchor
    if "CEVA" not in tu and "PYRAMID" not in tu and "捷飛運通" not in text:
        score = min(score, 0.2)
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 80) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="CEVA / Pyramid Lines (捷飛運通)")

    m = re.search(r"B/L no\s*:\s*(\S+)", text)
    if m:
        h.bl_no = m.group(1).strip()
        h.hbl_no = h.bl_no

    m = re.search(r"VESSEL\s*:\s*(.+?)\s{2,}VOYAGE\.\s*(\S+)", text)
    if m:
        h.vessel = m.group(1).strip()
        h.voyage = m.group(2).strip()
    else:
        m = re.search(r"VESSEL\s*:\s*([^\n]+)", text)
        if m:
            h.vessel = m.group(1).strip()
        m = re.search(r"VOYAGE\.\s*(\S+)", text)
        if m:
            h.voyage = m.group(1).strip()

    m = re.search(r"裝貨港\s*:\s*(\S+(?:\s+\S+)?)\s+卸貨港\s*:\s*(\S+)", text)
    if m:
        h.pol = m.group(1).strip()
        h.pod = m.group(2).strip()

    m = re.search(r"ETD\s*:\s*([\d/]+)", text)
    if m:
        h.etd = loose_date_to_iso(m.group(1))
    m = re.search(r"ETA\s*:\s*([\d/]+)", text)
    if m:
        h.eta = loose_date_to_iso(m.group(1))

    m = re.search(r"SHPR\s*:\s*([^\n]+)", text)
    if m:
        h.shipper = _snip(m.group(1))
    m = re.search(r"TO\.\s*:\s*([^\n]+)", text)
    if m:
        h.consignee = _snip(m.group(1))

    m = re.search(r"Container#\s+(.+?)\s+LOAD TYPE\s*:\s*(\S+)", text)
    if m:
        raw = m.group(1).strip().rstrip("*").strip()
        # drop trailing lone * container footnotes like *TLLU…
        raw = re.sub(r",\s*$", "", raw)
        h.container_nos = _snip(raw, 120)
        h.load_type = m.group(2).strip()
    else:
        m = re.search(r"LOAD TYPE\s*:\s*(\S+)", text)
        if m:
            h.load_type = m.group(1).strip()
        m = re.search(r"Container#\s+([^\n]+)", text)
        if m:
            h.container_nos = _snip(m.group(1).split("LOAD")[0].strip(" *,"), 120)

    m = re.search(r"Packings\s*:\s*([\d.]+)\s+(\S+)", text)
    if m:
        h.packages = us_float(m.group(1))
        h.package_unit = m.group(2).strip()

    m = re.search(r"G\.W\.:\s*([\d.]+)\s+KGS", text)
    if m:
        h.gross_weight_kg = us_float(m.group(1))

    m = re.search(r"Meas\s*:\s*([\d.]+)\s+CBM", text)
    if m:
        h.measurement_cbm = us_float(m.group(1))

    # Footnote extra container on same family (case4 *TLLU4399533)
    foot = re.search(r"\*([A-Z]{4}\d{7})", text)
    if foot and h.container_nos and foot.group(1) not in (h.container_nos or ""):
        h.container_nos = f"{h.container_nos}, {foot.group(1)}"

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="ceva_pyramid_arrival_v1",
            confidence="rules",
            needs_ocr=needs_ocr,
            doc_kind="arrival_notice",
            notes=NOTES if not h.bl_no else None,
        ),
    )
