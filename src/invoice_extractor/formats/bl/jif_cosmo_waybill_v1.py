"""Japan International Freight Forwarders (JIFFA form) / COSMO TRANS LINE waybill.

Samples (BHC 4th): case 6 ``BL.pdf`` (260918KEE103, Hitachi GLS MEH6J044,
16 PALLETS (4,815 PIECES) / 1,998.000 KGS) and case 8 ``WAYBILL.pdf`` +
scan ``20260921195744-0001.pdf`` (260918KEE102, HIPUS 117/121,
10 PALLETS (31,670 PIECES) / 3,084.500 KGS). Shimizu → Keelung, TVL
(Trans Van Links Express) as delivery agent.

The paper carries an anti-counterfeit background pattern, so Tesseract reads
of the description / weight block are noisy (``C0 PALLETS``, ``998, 000``,
``3,084, 50S``). Policy (same as ``kwe_sea_waybill_v1``): a value needs ≥2
agreeing reads (strict majority) or it is ``needs_gold`` with the suggested
value kept for the Summary BL columns.

Rule (user, 2026-09-29): only Result fields — BL No. / BL Packages / BL G.W.
"""

from __future__ import annotations

import re
from collections import Counter

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta

MATCH_HINTS = {
    "filename_regex": r"waybill|^bl\.pdf$",
    "keywords": [
        "Japan International",
        "COSMO TRANS LINE",
        "JIFFA MODEL FORM",
        "Waybill No.",
        "SHIPPER'S LOAD & COUNT SAID TO CONTAIN",
        "AS PER ATTACHED SHEET",
    ],
}

NOTES = (
    "Japan International Freight Forwarders (JIFFA form) / COSMO TRANS LINE "
    "non-negotiable waybill (BHC: Hitachi GLS, HIPUS; Shimizu → Keelung). "
    "Scanned / anti-counterfeit background → OCR. Output = BL No. / BL Packages / "
    "BL G.W. only. BL no = 6 digits + KEE + 3 digits (OCR spaces removed; also "
    "'HOUSE BL No.' on the attached sheet). Packages votes: 'N PALLETS (… PIECES)', "
    "'CONTAINER<N PALLETS', attached-sheet last 'CASE NO. N'. GW votes: "
    "'x,xxx.xxx' 3-dp weight in the SAID TO CONTAIN block. ≥2 agreeing reads, else "
    "needs_gold (suggested value kept). Vessel / voyage / ports / CBM not extracted."
)

RESULT_FIELDS = ("bl_no", "packages", "gross_weight_kg")

RULES_JSON = {
    "id": "jif_cosmo_waybill_v1",
    "doc_kind": "sea_waybill",
    "result_fields": list(RESULT_FIELDS),
    "header": {
        "bl_no": r"\d{6}KEE\d{3} (spaces stripped)",
        "packages_votes": [
            r"(\d+)\s*PALLETS?\s*\(\s*[\d,]+\s*PIECES",
            r"CONTAINER\s*<\s*(\d+)\s*PALLETS",
            r"CASE NO\.\s*(?:\d+\s*-\s*)?(\d+)  (attached sheet, last)",
        ],
        "gw_votes": [r"(\d{1,3}(?:,\s?\d{3})+\.\s?\d{3})|(\d{1,3}[,.]\s?\d{3})(?=\s|$)"],
    },
}

_BL_RE = re.compile(r"(\d[\d ]{5,8})\s*K\s*E\s*E\s*(\d[\d ]{2,4})")


def match_score(text: str, filename: str = "") -> float:
    t = text.upper()
    score = 0.0
    if "JAPAN INTERNATIONAL" in t:
        score += 0.3
    if "COSMO TRANS LINE" in t:
        score += 0.3
    if "JIFFA" in t or "IFFA MODEL FORM" in t:
        score += 0.15
    if "WAYBILL" in t.replace(" ", ""):
        score += 0.1
    if _bl_nos(text):
        score += 0.15
    if "COMMERCIAL INVOICE" in t or "PACKING LIST" in t:
        score -= 0.5
    return max(0.0, min(score, 1.0))


def _bl_nos(text: str) -> list[str]:
    out = []
    for m in _BL_RE.finditer(text):
        a = m.group(1).replace(" ", "")
        b = m.group(2).replace(" ", "")
        if len(a) == 6 and len(b) == 3:
            out.append(f"{a}KEE{b}")
    return out


def _vote(reads: list[tuple[str, float | None]]) -> tuple[float | None, bool, str]:
    vals = [v for _, v in reads if v is not None]
    detail = ", ".join(f"{s}={v:g}" for s, v in reads if v is not None) or "no reads"
    if not vals:
        return None, False, detail
    c = Counter(vals)
    (best, n), *rest = c.most_common()
    confident = n >= 2 and n * 2 > len(vals)
    if rest and rest[0][1] == n:
        confident = False
    return best, confident, detail


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader()
    notes: list[str] = []
    ng: list[str] = []

    nos = _bl_nos(text)
    if nos:
        c = Counter(nos)
        (best, n), *rest = c.most_common()
        h.bl_no = best
        if rest:
            ng.append("bl_no")
            notes.append(f"waybill no reads {dict(c)}")
    else:
        ng.append("bl_no")

    # --- packages ---
    pk: list[tuple[str, float | None]] = []
    m = re.search(r"\b(\d{1,3})\s*PALLETS?\s*\(\s*[\d,\s]+PIECES", text, re.I)
    if m:
        pk.append(("pallets(pieces)", float(m.group(1))))
    m = re.search(r"CONTAINER\s*[<(]\s*(\d{1,3})\s*PALLETS", text, re.I)
    if m:
        pk.append(("container<pallets", float(m.group(1))))
    cases = re.findall(r"CASE\s*NO\.?\s*(?:\d{1,3}\s*-\s*)?(\d{1,3})\b", text, re.I)
    if cases:
        pk.append(("attached_sheet_last_case_no", float(max(int(x) for x in cases))))
    pkg, pkg_ok, pkg_detail = _vote(pk)
    h.packages = pkg
    if not pkg_ok:
        ng.append("packages")
    notes.append(f"pkg reads: {pkg_detail}")

    # --- GW: 3-dp weight on the first lines under "SAID TO CONTAIN" ---
    # (the trailing number on that line is the measurement M3, e.g. 10.479).
    gw: list[tuple[str, float | None]] = []
    partial: list[str] = []
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        # header cell is upper-case; the terms text "said to contain the cargo" is not
        if not re.search(r"SAID\s*TO\s*CONTAIN", ln):
            continue
        for nxt in lines[i + 1:i + 4]:
            full = re.search(r"(?<![\d,.])(\d{1,3})[,.]\s?(\d{3})[,.]\s?(\d{3})(?![\d])", nxt)
            if full:
                v = int(full.group(1)) * 1000 + int(full.group(2)) + int(full.group(3)) / 1000
                gw.append(("said_to_contain", round(v, 3)))
                break
            nums = re.findall(r"(?<![\d,.])\d{1,3}[,.]\s?\d{3}(?![\d])", nxt)
            if len(nums) >= 2:
                # weight + measurement, but the weight lost its thousands group
                partial.append(nums[0])
                break
        break
    g, gw_ok, gw_detail = _vote(gw)
    h.gross_weight_kg = g
    if not gw_ok:
        ng.append("gross_weight_kg")
    notes.append(f"GW reads: {gw_detail}")
    if partial:
        notes.append(f"GW partial OCR read(s) {partial} (incomplete — digits lost under the background pattern)")

    needs_gold = bool(ng)
    if needs_gold:
        notes.insert(0, "needs_gold: " + ", ".join(ng) + " (OCR reads disagree / too few; anti-counterfeit background)")
    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="jif_cosmo_waybill_v1",
            confidence="needs_gold" if needs_gold else "rules",
            needs_ocr=needs_ocr,
            needs_gold=needs_gold,
            needs_gold_fields=ng or None,
            notes="; ".join(notes),
            doc_kind="sea_waybill",
        ),
    )
