"""Kintetsu World Express (KWE) / APL Logistics SEA WAYBILL — MA RB JP sea (90-KWE-26MA-*).

Samples (MA 3rd, RBJPsea): ``robert bosch.pdf`` / ``bosch bosch.pdf`` /
``2018_001.pdf`` / ``2986_001 (1).pdf`` — copier scans, 2 pages:
page 1 = SEA WAYBILL NON-NEGOTIABLE (WAYBILL NO. 1220########, BOSCH
CORPORATION Yokohama → KEELUNG, LCL consolidation), page 2 = KWE freight
invoice (請求書, B/L No. / PCS / KG / M3) or an ATTACHED SHEET (marks + INV#).
Text layer is empty (14) or scanner CJK-mode mojibake (6) → Tesseract OCR.

≠ ``kwe_air_waybill_v1`` (IATA air waybill 1220-########, SOE HAWC).

Rule (user, 2026-09-29): only fields present in ``InvoiceExtract_Result`` are
extracted — for a BL that is BL No. / BL Packages / BL G.W.
"""

from __future__ import annotations

import re
from collections import Counter

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta

MATCH_HINTS = {
    "filename_regex": r"robert bos|bosch bosch|^\d{4}_\d{3}",
    "keywords": [
        "KINTETSU WORLD EXPRESS",
        "APL LOGISTICS",
        "SEA WAYBILL NON-NEGOTIABLE",
        "WAYBILL NO.",
        "SAID TO CONTAIN",
        "TOTAL NOS. OF PACKAGES",
    ],
}

NOTES = (
    "KWE / APL Logistics sea waybill (MA RB JP 90-KWE, BOSCH CORPORATION → "
    "ROBERT BOSCH TAIWAN, Yokohama → Keelung). Scanned: OCR text. Output = "
    "InvoiceExtract_Result BL columns only: BL No. / BL Packages / BL G.W. "
    "BL no = WAYBILL NO. 1220######## (12 digits; majority of face/footer/page-2 "
    "B/L No. reads). Packages and GW are OCR-voted: packages from NOS. OF PKGS "
    "('N SAID TO CONTAIN'), 'N PACKAGES/PALLETS' body, pallet+carton breakdown "
    "'(P PALLETS(= C CARTONS), L CARTONS)', TOTAL words '(N) PACKAGES ONLY' and "
    "page-2 'N PCS'; GW from 'SAID TO CONTAIN: X', TOTAL row and page-2 'X KG'. "
    "A value needs ≥2 agreeing reads and a strict majority, else needs_gold "
    "(suggested value kept). Vessel / voyage / ETD / ports / CBM / invoice refs "
    "are NOT extracted (not Result columns)."
)

# Only fields that exist in InvoiceExtract_Result (Summary BL columns).
RESULT_FIELDS = ("bl_no", "packages", "gross_weight_kg")

RULES_JSON = {
    "id": "kwe_sea_waybill_v1",
    "doc_kind": "sea_waybill",
    "result_fields": list(RESULT_FIELDS),
    "header": {
        "bl_no": r"1220\d{8}(?!\d)",
        "packages_votes": [
            r"(\d+)\s+SAID TO CONTAIN",
            r"SAID TO CONTAIN[^\n]*\n[^\n]*?(\d+)\s*_?\s*(?:PACKAGES|PALLETS)\b",
            r"\(\s*(\d+)\s*PALLETS?\s*\(=?\s*\d+\s*CARTONS?\)\s*[,&]?\s*(\d+)?\s*CARTONS?",
            r"\((\d+)\)\s*(?:PACKAGES|PALLETS)",
            r"(\d+)\s*PC[Ss]\b",
        ],
        "gw_votes": [
            r"SAID TO CONTAIN:?\s+([\d,]+\.\s?\d{2})",
            r"(?:IN WORDS|ONLY)[^\n]*?([\d,]+\.\s?\d{2})\s+[\d.,%]+\s*$",
            r"PC[Ss]\s+([\d,]+\.\d{2})\s*KG",
        ],
    },
}

_WORDNUM = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7,
    "EIGHT": 8, "NINE": 9, "TEN": 10, "ELEVEN": 11, "TWELVE": 12, "THIRTEEN": 13,
    "FOURTEEN": 14, "FIFTEEN": 15, "SIXTEEN": 16, "SEVENTEEN": 17, "EIGHTEEN": 18,
    "NINETEEN": 19, "TWENTY": 20, "THIRTY": 30, "FORTY": 40, "FIFTY": 50,
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    t = text.upper()
    if "KINTETSU WORLD EXPRESS" in t:
        score += 0.35
    if "SEA WAYBILL" in t or "SEAWAYBILL" in t:
        score += 0.3
    if "APL LOGISTICS" in t or "D/B/AAPL" in t:
        score += 0.1
    if re.search(r"1220\d{8}(?!\d)", text):
        score += 0.15
    if "SAID TO CONTAIN" in t:
        score += 0.1
    # air waybill / other forwarders
    if "AIR WAYBILL" in t or "AIRPORT OF DEPARTURE" in t:
        score -= 0.6
    if "NIPPON EXPRESS" in t or "MAERSK LOGISTICS" in t:
        score -= 0.5
    if "ARRIVAL NOTICE" in t and "KINTETSU" not in t:
        score -= 0.4
    return max(0.0, min(score, 1.0))


def _vote(reads: list[tuple[str, float]]) -> tuple[float | None, bool, str]:
    """Return (value, confident, detail). Confident = ≥2 agreeing reads and strict majority."""
    vals = [v for _, v in reads if v is not None]
    detail = ", ".join(f"{src}={v:g}" for src, v in reads if v is not None) or "no reads"
    if not vals:
        return None, False, detail
    c = Counter(vals)
    (best, n), *rest = c.most_common()
    confident = n >= 2 and n * 2 > len(vals)
    if rest and rest[0][1] == n:
        confident = False
    return best, confident, detail


def _num(s: str) -> float | None:
    s = s.replace(" ", "")
    return us_float(s)


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader()
    notes: list[str] = []
    needs_gold_fields: list[str] = []

    # --- BL / waybill no (12 digits, OCR may glue a stray digit in front) ---
    nos = re.findall(r"1220\d{8}(?!\d)", text)
    if nos:
        c = Counter(nos)
        (best, n), *rest = c.most_common()
        h.bl_no = best
        if rest and rest[0][1] == n or n < 2:
            needs_gold_fields.append("bl_no")
            notes.append(f"waybill no reads {dict(c)}")

    # --- packages votes ---
    pk: list[tuple[str, float]] = []
    m = re.search(r"(\d{1,3})\s+SAID TO CONTAIN", text)
    if m:
        pk.append(("nos_of_pkgs", float(m.group(1))))
    m = re.search(
        r"SAID TO CONTAIN[^\n]*\n[^\n]*?\b(\d{1,3})\s*[_|]?\s*(?:PACKAGES|PALLETS)\b(?!\s*\()",
        text,
    )
    if m:
        pk.append(("body", float(m.group(1))))
    # "(4 PALLETS(= 46 CARTONS) ,1 CARTON)" — loose cartons may wrap to the
    # next line behind a marks number: "(5 PALLETS(= 123 CARTONS),\n 9843… 3 CARTONS)"
    m = re.search(
        r"\(\s*(\d{1,3})\s*PALLETS?\s*\(\s*=?\s*\d+\s*CARTONS?\s*\)\s*[,&]?"
        r"[^\S\n]*(?:\n[^\n]*?){0,2}\b(\d{1,3})\s*CARTONS?\s*\)",
        text,
    )
    if not m:
        m = re.search(r"\b(\d{1,3})\s*PALLETS?\s*\(\s*=?\s*\d+\s*CARTONS?\s*\)()", text)
    if m:
        pal = int(m.group(1))
        loose = int(m.group(2)) if m.group(2) else 0
        pk.append(("pallet+carton", float(pal + loose)))
    m = re.search(r"\((\d{1,3})\)\s*(?:PACKAGES|PALLETS)", text)
    if m:
        pk.append(("total_words", float(m.group(1))))
    else:
        m = re.search(
            r"TOTAL NOS\.? OF PACKAGES[^\n]*?\b(" + "|".join(_WORDNUM) + r")\b", text
        )
        if m:
            pk.append(("total_words", float(_WORDNUM[m.group(1)])))
    m = re.search(r"(?m)^\s*(\d{1,3})\s*PC[Ss]\b", text)
    if m:
        pk.append(("page2_pcs", float(m.group(1))))
    pkg, pkg_ok, pkg_detail = _vote(pk)
    h.packages = pkg
    if not pkg_ok:
        needs_gold_fields.append("packages")
    notes.append(f"pkg reads: {pkg_detail}")

    # --- GW votes ---
    gw: list[tuple[str, float]] = []
    m = re.search(r"SAID TO CONTAIN:?\s+([\d,]+\.\s?\d{2})", text)
    if m:
        gw.append(("row", _num(m.group(1))))
    for ln in text.splitlines():
        if re.search(r"IN WORDS|PACKAGES ONLY|PALLETS ONLY|\bONLY\b", ln):
            mm = re.search(r"([\d,]+\.\s?\d{2})\s+[\d.,%]+\s*$", ln)
            if mm:
                gw.append(("total_row", _num(mm.group(1))))
                break
    m = re.search(r"PC[Ss]\s+([\d,]+\.\d{2})\s*KG", text)
    if m:
        gw.append(("page2_kg", _num(m.group(1))))
    g, gw_ok, gw_detail = _vote(gw)
    h.gross_weight_kg = g
    if not gw_ok:
        needs_gold_fields.append("gross_weight_kg")
    notes.append(f"GW reads: {gw_detail}")

    needs_gold = bool(needs_gold_fields)
    if needs_gold:
        notes.insert(0, "needs_gold: " + ", ".join(needs_gold_fields) + " (OCR reads disagree / too few)")
    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="kwe_sea_waybill_v1",
            confidence="needs_gold" if needs_gold else "rules",
            needs_ocr=needs_ocr,
            needs_gold=needs_gold,
            needs_gold_fields=needs_gold_fields or None,
            notes="; ".join(notes),
            doc_kind="sea_waybill",
        ),
    )
