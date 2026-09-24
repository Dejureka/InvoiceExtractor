"""Hippopo Global Logistics — Taiwan ARRIVAL NOTICE 到貨通知書 v1.

BHC 3rd cases 1/3/6: ``到貨通知.pdf`` with B/L NO : CPSE… / P076….
Distinct from ``hippopo_hbl_v1`` (HBL draft HB######## face).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta, loose_date_to_iso

MATCH_HINTS = {
    "filename_regex": r"到貨通知|arrival",
    "keywords": [
        "HIPPOPO GLOBAL LOGISTICS",
        "ARRIVAL NOTICE",
        "到貨通知書",
        "河馬新創",
        "B/L",
    ],
}

NOTES = (
    "Hippopo Taiwan arrival notice (到貨通知書). B/L nos CPSE*/P076* etc. "
    "Samples: BHC 3rd case1/3/6 到貨通知.pdf."
)

RULES_JSON = {
    "id": "hippopo_arrival_v1",
    "doc_kind": "arrival_notice",
    "header": {
        "bl_no": r"B/L\s+NO\s*:\s*(\S+)",
        "packages": r"(\d+)\s+(?:PLTS|PALLETS|CARTONS)",
        "gross_weight_kg": r"([\d,]+\.\d{2})\s*KGS",
        "eta": r"抵港日期\s*([\d/]+)",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    tu = text.upper()
    if "到貨" in filename:
        score += 0.15
    if "ARRIVAL NOTICE" in tu or "到貨通知書" in text:
        score += 0.2
    if "HIPPOPO" in tu or "河馬" in text:
        score += 0.5
    if re.search(r"B/L\s+NO\s*:", text, re.I):
        score += 0.15
    # Must be Hippopo family — do not match generic OCR "ARRIVAL" noise
    if "HIPPOPO" not in tu and "河馬" not in text:
        return 0.0
    if re.search(r"\bHB\d{8}\b", text) and "ARRIVAL" not in tu:
        score -= 0.3  # prefer hippopo_hbl_v1 for draft face
    if "CEVA LOGISTICS" in tu or "PYRAMID LINES" in tu:
        score -= 0.7
    if "MILESTONE FORWARDING" in tu or "里運國際" in text:
        score -= 0.7
    if "DHL GLOBAL FORWARDING" in tu and "HIPPOPO" not in tu:
        score -= 0.5
    if "CHINA PROGRESS" in tu:
        score -= 0.6
    return max(0.0, min(score, 1.0))


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="Hippopo Global Logistics Co., Ltd.")

    m = re.search(r"B/L\s+NO\s*:\s*(\S+)", text, re.I)
    if m:
        h.bl_no = m.group(1).strip()
        h.hbl_no = h.bl_no

    m = re.search(r"Shipper\s*\n\s*:?\s*([A-Z][^\n]{5,90})", text, re.I)
    if m:
        ship = re.sub(r"\s*B/L\s+NO.*$", "", m.group(1), flags=re.I).strip(" ,:")
        h.shipper = _snip(ship)

    m = re.search(r"Consignee\s*\n\s*:?\s*([A-Z][^\n]{5,90})", text, re.I)
    if m:
        h.consignee = _snip(m.group(1).strip(" :"))

    m = re.search(
        r"Ocean Vessel\s+VOY\.?\s*NO\.?\s*\n\s*([A-Z0-9 ]+?)\s+(\d+\w*)\s+",
        text,
        re.I,
    )
    if m:
        h.vessel = re.sub(r"\s+", " ", m.group(1)).strip()
        h.voyage = m.group(2)

    m = re.search(r"Port of Loading\s+Port of Discharge[^\n]*\n\s*([A-Z][^\n,]+)", text, re.I)
    if m:
        h.pol = _snip(m.group(1))
    if re.search(r"KEELUNG", text, re.I):
        h.pod = "KEELUNG, TAIWAN"

    m = re.search(r"抵港日期\s*\n?\s*([\d/]+)", text)
    if m:
        h.eta = loose_date_to_iso(m.group(1)) or m.group(1)

    # Packages: prefer summed PLTS/CARTONS on cargo lines; handle multi-container
    # Per-container pkg counts appear on cargo lines like "18 PLTS" before the
    # vessel/SERVICE block; sum all of them when multiple containers.
    cargo = text
    m_svc = re.search(r"SERVICE TYPE", text, re.I)
    if m_svc:
        cargo = text[: m_svc.start()]
    pkgs = re.findall(r"(\d+)\s+PLTS", cargo, re.I)
    carts = re.findall(r"(\d+)\s+CARTONS", cargo, re.I)
    if pkgs:
        vals = [float(x) for x in pkgs]
        h.packages = float(sum(vals)) if len(vals) > 1 else float(vals[0])
        h.package_unit = "PLTS"
    elif carts:
        vals = [float(x) for x in carts]
        h.packages = float(sum(vals)) if len(vals) > 1 else float(vals[0])
        h.package_unit = "CARTONS"

    # Gross weight: prefer the standalone total line (largest / last xx.xx KGS before SERVICE)
    weights = [us_float(w) for w in re.findall(r"([\d,]+\.\d{2})\s*KGS", text, re.I)]
    weights = [w for w in weights if w]
    if weights:
        # case3 has per-container then total 6,937.40 — take max
        h.gross_weight_kg = max(weights)

    # Invoice refs
    refs = []
    for rx in (r"INV\s*No\.?\s*([A-Z0-9-]+)", r"\b(SATJG\w+)\b", r"\b(ST\d{7})\b", r"\b(OHIZUMI[-\w]+)\b"):
        for mm in re.finditer(rx, text, re.I):
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
            format_id="hippopo_arrival_v1",
            confidence=conf,
            needs_ocr=needs_ocr,
            needs_gold=needs_gold,
            doc_kind="arrival_notice",
            notes=NOTES if conf == "rules" else "Hippopo arrival partial",
        ),
    )
