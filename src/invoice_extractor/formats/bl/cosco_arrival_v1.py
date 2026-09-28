"""COSCO SHIPPING Lines (中國遠洋 Taiwan) arrival notice — MA RB DE sea (90-C-26MA-*).

Samples (MA 3rd, RBDEsea): ``BL6437826540.PDF`` … ``BL6449088340.PDF`` —
one 到貨通知 / ARRIVAL NOTICE per 90-C folder, Rotterdam → Taipei Port /
Keelung / Kaohsiung, shipper COSCO SHIPPING LOGISTICS (EUROPE), notify
Robert Bosch GmbH. Text layer (no OCR).
"""

from __future__ import annotations

import re

from invoice_extractor.schema import en_date_to_iso, us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta

MATCH_HINTS = {
    "filename_regex": r"^BL\d{10}",
    "keywords": [
        "ARRIVAL NOTICE",
        "到貨通知",
        "B/L Number: COSU",
        "COSCO SHIPPING",
        "CHINA COSCO SHIPPING CO., LTD. (TAIWAN)",
        "ETA AT POD",
        "Total:",
    ],
}

NOTES = (
    "COSCO SHIPPING Lines Taiwan arrival notice (到貨通知 / ARRIVAL NOTICE, "
    "Sea WayBill). BL no = 'B/L Number: COSU##########' (filename BL + 10 digits "
    "= same number without COSU). Packages / GW = attachment-sheet "
    "'Total: N Packages … X KG' (cross-checked against the first-page container "
    "row 箱型/毛重/總件數); ETA = 'ETA AT POD: <port>' + 'ON: <weekday>, DD Mon, YYYY'. "
    "Container + seal from the 20GP/40HQ row. Invoice refs = 'invoice number:' list "
    "(MA Document No. 2120xxxxxx). Samples: MA 3rd RBDEsea 90-C-26MA-007 … 264."
)

RULES_JSON = {
    "id": "cosco_arrival_v1",
    "doc_kind": "arrival_notice",
    "header": {
        "bl_no": r"B/L Number:\s*(COSU\d{10})",
        "packages": r"Total:\s+(\d+)\s+([\d,.]+)\s*KG",
        "gross_weight_kg": r"Total:\s+\d+\s+([\d,.]+)\s*KG",
        "eta": r"ON:\s*\w+,\s*(\d{1,2} \w{3},? \d{4})",
        "container_row": r"^(20|40|45)(GP|HQ|HC|RF|OT|FR)\s+([\d.]+)\s+(\d+)\s+([A-Z]{4}\d{7})",
        "invoice_refs": r"invoice number:\s*((?:\s*\d{10})+)",
    },
}

_CONT_ROW = re.compile(
    r"(?m)^\s*((?:20|40|45)(?:GP|HQ|HC|RF|OT|FR|DC))\s+([\d,.]+)\s+(\d+)\s+([A-Z]{4}\d{7})\b"
)


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    if re.match(r"^BL\d{10}\b", filename or "", re.I):
        score += 0.15
    if "ARRIVAL NOTICE" in text or "到貨通知" in text:
        score += 0.2
    if re.search(r"B/L Number:\s*COSU\d{10}", text):
        score += 0.4
    if "COSCO SHIPPING" in text or "中國遠洋" in text:
        score += 0.25
    if "ETA AT POD" in text:
        score += 0.1
    # other arrival-notice families
    if "MILESTONE FORWARDING" in text or "里運國際" in text:
        score -= 0.6
    if "CEVA LOGISTICS" in text or "PYRAMID LINES" in text:
        score -= 0.6
    if "DHL GLOBAL FORWARDING" in text or "HIPPOPO" in text.upper():
        score -= 0.6
    # MA invoices mention nothing of this, but guard anyway
    if "Document No.:" in text and "Goods value" in text:
        score -= 0.6
    return max(0.0, min(score, 1.0))


def _after_label_block(lines: list[str], label: str) -> list[str]:
    for i, ln in enumerate(lines):
        if label in ln:
            return lines[i + 1 : i + 4]
    return []


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="COSCO SHIPPING Lines (中國遠洋 Taiwan)")
    notes: list[str] = []
    needs_gold = False
    lines = text.splitlines()

    m = re.search(r"B/L Number:\s*(COSU\d{10})", text)
    if m:
        h.bl_no = m.group(1)
        h.mbl_no = m.group(1)

    # Vessel / voyage: block under 船名/航次VESSEL/VOYAGE (left column)
    blk = _after_label_block(lines, "VESSEL/VOYAGE ARRIVING AT POD")
    if len(blk) >= 2:
        v = re.split(r"\s{2,}", blk[0].strip())[0]
        voy = re.split(r"\s{2,}", blk[1].strip())[0]
        h.vessel = v or None
        h.voyage = voy or None
    if not h.vessel:
        m = re.search(r"B/L Vessel/Voyage:\s*\n(?:.*?\s{2,})?([A-Z][A-Z .]+?)\s+(\S+)\s*$", text, re.M)
        if m:
            h.vessel, h.voyage = m.group(1).strip(), m.group(2)

    m = re.search(r"ETA AT POD:\s*([A-Za-z .]+?)\s{2,}", text)
    if m:
        h.pod = m.group(1).strip()
    m = re.search(r"\bON:\s*[A-Za-z]+,\s*(\d{1,2})\s+([A-Za-z]{3}),?\s+(\d{4})", text)
    if m:
        h.eta = en_date_to_iso(f"{m.group(2)} {m.group(1)}, {m.group(3)}")
    blk = _after_label_block(lines, "PORT OF LOADING")
    if blk:
        parts = re.split(r"\s{2,}", blk[0].strip())
        if len(parts) >= 2:
            h.pol = parts[-1]

    # Container rows (page 1) and attachment Total
    rows = _CONT_ROW.findall(text)
    conts: list[str] = []
    row_pkg = 0.0
    row_gw = 0.0
    for ctype, gw_s, pkg_s, cno in rows:
        if cno in conts:
            continue
        conts.append(cno)
        row_pkg += float(pkg_s)
        row_gw += us_float(gw_s) or 0.0
        seal = None
        # seal on the next line under the container no
        for i, ln in enumerate(lines):
            if cno in ln and i + 1 < len(lines):
                sm = re.search(r"\b([A-Z]{1,3}\d{5,8})\b", lines[i + 1])
                if sm:
                    seal = sm.group(1)
                break
        conts[-1] = f"{cno}/{seal}" if seal else cno
    if conts:
        h.container_nos = ", ".join(conts)
    if rows and re.search(r"[A-Z]{4}\d{7}\s+FCL\b", text):
        h.load_type = "FCL"
    elif rows and re.search(r"[A-Z]{4}\d{7}\s+LCL\b", text):
        h.load_type = "LCL"

    tot = re.search(r"Total:\s+(\d+)\s+([\d,.]+)\s*KG", text)
    tot_pkg = float(tot.group(1)) if tot else None
    tot_gw = us_float(tot.group(2)) if tot else None
    if tot_pkg is not None:
        h.packages = tot_pkg
        h.gross_weight_kg = tot_gw
    elif rows:
        h.packages = row_pkg
        h.gross_weight_kg = round(row_gw, 3)
        notes.append("no attachment 'Total:' line; packages/GW = sum of container rows")
    if tot_pkg is not None and rows:
        if abs(tot_pkg - row_pkg) > 0.001 or abs((tot_gw or 0) - row_gw) > 0.01:
            needs_gold = True
            notes.append(
                f"Total {tot_pkg:g}/{tot_gw} ≠ container rows {row_pkg:g}/{round(row_gw, 3)}"
            )
    m = re.search(r"Packages\s+([\d.]+)\s*CBM", text)
    if m:
        h.measurement_cbm = us_float(m.group(1))
    h.package_unit = "PACKAGES"

    m = re.search(r"invoice number:\s*\n((?:\s*\d{10}\s*\n)+)", text, re.I)
    if m:
        h.invoice_refs = ", ".join(re.findall(r"\d{10}", m.group(1)))

    if "COSCO SHIPPING LOGISTICS (EUROPE)" in text:
        h.shipper = "COSCO SHIPPING LOGISTICS (EUROPE) GmbH"
    if "Robert Bosch Taiwan Co., Ltd" in text:
        h.consignee = "Robert Bosch Taiwan Co., Ltd"
    if "Robert Bosch GmbH" in text:
        h.notify = "Robert Bosch GmbH"

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="cosco_arrival_v1",
            confidence="needs_gold" if needs_gold else "rules",
            needs_ocr=needs_ocr,
            needs_gold=needs_gold,
            notes="; ".join(notes) or None,
            doc_kind="arrival_notice",
        ),
    )
