"""COSCO SHIPPING Lines (中國遠洋 Taiwan) arrival notice — MA RB DE sea (90-C-26MA-*).

Samples (MA 3rd, RBDEsea): ``BL6437826540.PDF`` … ``BL6449088340.PDF`` —
one 到貨通知 / ARRIVAL NOTICE per 90-C folder, Rotterdam → Taipei Port /
Keelung / Kaohsiung, shipper COSCO SHIPPING LOGISTICS (EUROPE), notify
Robert Bosch GmbH. Text layer (no OCR).

Rule (user, 2026-09-29): only fields present in ``InvoiceExtract_Result`` are
extracted — for a BL that is BL No. / BL Packages / BL G.W.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
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
    "Sea WayBill). Output = InvoiceExtract_Result BL columns only: BL No. / "
    "BL Packages / BL G.W. BL no = 'B/L Number: COSU##########' (filename BL + "
    "10 digits = same number without COSU). Packages / GW = attachment-sheet "
    "'Total: N Packages … X KG', cross-checked against the first-page container "
    "row(s) 箱型/毛重/總件數 (mismatch → needs_gold). Vessel / voyage / ETA / "
    "ports / container / CBM / invoice refs are NOT extracted (not Result "
    "columns). Samples: MA 3rd RBDEsea 90-C-26MA-007 … 264."
)

# Only fields that exist in InvoiceExtract_Result (Summary BL columns).
RESULT_FIELDS = ("bl_no", "packages", "gross_weight_kg")

RULES_JSON = {
    "id": "cosco_arrival_v1",
    "doc_kind": "arrival_notice",
    "result_fields": list(RESULT_FIELDS),
    "header": {
        "bl_no": r"B/L Number:\s*(COSU\d{10})",
        "packages": r"Total:\s+(\d+)\s+([\d,.]+)\s*KG",
        "gross_weight_kg": r"Total:\s+\d+\s+([\d,.]+)\s*KG",
        "check_container_row": r"^(20|40|45)(GP|HQ|HC|RF|OT|FR)\s+([\d.]+)\s+(\d+)\s+([A-Z]{4}\d{7})",
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


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader()
    notes: list[str] = []
    needs_gold = False

    m = re.search(r"B/L Number:\s*(COSU\d{10})", text)
    if m:
        h.bl_no = m.group(1)

    # Page-1 container rows: used only to cross-check the attachment Total.
    rows = _CONT_ROW.findall(text)
    seen: set[str] = set()
    row_pkg = 0.0
    row_gw = 0.0
    for _ctype, gw_s, pkg_s, cno in rows:
        if cno in seen:
            continue
        seen.add(cno)
        row_pkg += float(pkg_s)
        row_gw += us_float(gw_s) or 0.0

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

    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="cosco_arrival_v1",
            confidence="needs_gold" if needs_gold else "rules",
            needs_ocr=needs_ocr,
            needs_gold=needs_gold,
            needs_gold_fields=["packages", "gross_weight_kg"] if needs_gold else None,
            notes="; ".join(notes) or None,
            doc_kind="arrival_notice",
        ),
    )
