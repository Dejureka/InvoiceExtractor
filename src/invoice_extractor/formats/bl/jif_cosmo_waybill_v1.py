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

BHC 6th (2026-10-08): same JIFFA model form issued by OCEAN LINKS LTD. for
Saginomiya (case10 scan ``20260929202543-0001.pdf``, waybill ``KLG-T268Y98``,
``1 CONTAINER<5 PALLETS(131 CARTONS)>`` / 1,460.900 KGS, Yokohama → Keelung);
HIPUS ``4 PALLETS(8,959 PIECES) & 2 CASES`` / ``1 CONTAINER<6 PACKAGES>`` = 6.

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
        "OCEAN LINKS LTD",
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
    "'x,xxx.xxx' 3-dp weight in the SAID TO CONTAIN block. Reads come from the page pass, "
    "a second pass with the hatch background removed, and single-line re-reads of the "
    "located weight at 300/400/600 dpi (Auditor 2026-10-05: clear print must not stay "
    "needs_gold). ≥2 agreeing reads (strict majority), else "
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
            r"CONTAINER\s*<\s*(\d+)\s*(?:PALLETS|PACKAGES)",
            r"N PALLETS(… PIECES) & M CASES → N+M",
            r"SAY : ONE(1)PALLET ONLY",
            r"CASE NO\.\s*(?:\d+\s*-\s*)?(\d+)  (attached sheet, last)",
        ],
        "gw_votes": [r"(\d{1,3}(?:,\s?\d{3})+\.\s?\d{3})|(\d{1,3}[,.]\s?\d{3})(?=\s|$)"],
    },
}

_BL_RE = re.compile(r"(\d[\d ]{5,8})\s*K\s*E\s*E\s*(\d[\d ]{2,4})")
# Ocean Links waybill no "KLG-T268Y98"
_BL_OL_RE = re.compile(r"\b(KLG\s?-\s?[A-Z0-9]{7,8})\b")


def match_score(text: str, filename: str = "") -> float:
    t = text.upper()
    score = 0.0
    if "JAPAN INTERNATIONAL" in t:
        score += 0.3
    if "COSMO TRANS LINE" in t:
        score += 0.3
    if "OCEAN LINKS" in t:
        score += 0.4
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
    for m in _BL_OL_RE.finditer(text):
        out.append(re.sub(r"\s", "", m.group(1)))
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


_SAY_WORDS = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7,
    "EIGHT": 8, "NINE": 9, "TEN": 10, "ELEVEN": 11, "TWELVE": 12,
}

_GW3_RX = re.compile(r"(?<![\d,.])(\d{1,3})[,.]\s?(\d{3})[,.]\s?(\d{3})(?![\d])")
_DIG = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1"})
# count glyph inside "CONTAINER<S PALLETS" (OCR S = 5, BHC 6th case10)
_DIG_CNT = str.maketrans({"O": "0", "o": "0", "I": "1", "l": "1", "S": "5"})


def _gw3(s: str) -> float | None:
    m = _GW3_RX.search(s)
    if not m:
        return None
    return round(int(m.group(1)) * 1000 + int(m.group(2)) + int(m.group(3)) / 1000, 3)


def _pass_reads(text: str, tag: str) -> tuple[list, list, list]:
    """One OCR pass → (pkg reads, GW reads, partial GW strings)."""
    pk: list[tuple[str, float | None]] = []
    # "16 PALLETS (4,815 PIECES)"; cleaned pass may break the line before "(" and
    # prefix a stray glyph ("Bo 16 PALLETS\na (4,815 PIECES)", "¢10 PALLETS(31, 670")
    m = re.search(r"\b(\d{1,3})\s*PALLETS?\s*(?:\n[^\n(]{0,4})?\(\s*[\d,\s]+(?:PIECES|CARTONS)\s*\)?", text, re.I)
    if m and int(m.group(1)) > 0:
        n = int(m.group(1))
        # BHC 6th case9: "4 PALLETS(8,959 PIECES) & 2 CASES" → 6 packages
        mc = re.match(r"\s*&\s*(\d{1,3})\s*(?:CASES?|CARTONS?|CRATES?|SKIDS?)\b", text[m.end():], re.I)
        if mc:
            n += int(mc.group(1))
        pk.append((f"pallets(pieces)_{tag}", float(n)))
    m = re.search(r"CONTAINER\s*[<(]\s*([\dOoIlS]{1,3})\s*(?:PALLETS|PACKAGES)", text, re.I)
    if m and m.group(1).translate(_DIG_CNT).isdigit():
        pk.append((f"container<pallets_{tag}", float(m.group(1).translate(_DIG_CNT))))
    # BHC 6th case8: "SAY :ONE(1)PALLET ONLY." (OCR "ONE(IDPALLET", "0NE(1)PALLET")
    m = re.search(
        r"SAY\s*:?\s*([A-Z0]{3,9})\s*\(\s*([\dIlD]{1,3})\s*\)?\s*(?:PALLETS?|PACKAGES?|CASES?)\b",
        text,
    )
    if m:
        w = _SAY_WORDS.get(m.group(1).replace("0", "O"))
        d = m.group(2).translate(_DIG).replace("D", "")
        if w:
            pk.append((f"say_words_{tag}", float(w)))
        elif d.isdigit() and int(d) > 0:
            pk.append((f"say_digits_{tag}", float(d)))
    cases = re.findall(r"CASE\s*NO\.?\s*(?:\d{1,3}\s*-\s*)?(\d{1,3})\b", text, re.I)
    if cases:
        pk.append((f"attached_sheet_last_case_no_{tag}", float(max(int(x) for x in cases))))
    # GW: 3-dp weight on the first lines under "SAID TO CONTAIN"
    # (the trailing number on that line is the measurement M3, e.g. 10.479).
    gw: list[tuple[str, float | None]] = []
    partial: list[str] = []
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        # header cell is upper-case; the terms text "said to contain the cargo" is not
        if not re.search(r"SAID\s*TO\s*CONTAIN", ln):
            continue
        for nxt in lines[i + 1:i + 4]:
            v = _gw3(nxt)
            if v is not None:
                gw.append((f"said_to_contain_{tag}", v))
                break
            nums = re.findall(r"(?<![\d,.])\d{1,3}[,.]\s?\d{3}(?![\d])", nxt)
            if len(nums) >= 2:
                # weight + measurement, but the weight lost its thousands group
                partial.append(nums[0])
                break
        break
    return pk, gw, partial


def _clean_passes(path: str, backend: str) -> tuple[list[tuple[str, str]], list[tuple[str, float]], list[str]]:
    """Extra reads on the face page with the anti-counterfeit hatch removed.

    Root cause of BHC 4th case6/8 (Auditor 2026-10-05): the waybill paper's
    background is fine horizontal hatch lines; the page pass reads ``998, 000``
    (thousands group lost) or nothing, so GW had ≤1 read and stayed needs_gold
    although the print is clear. A vertical opening (k=3 px @300 dpi) drops the
    1–2 px hatch and keeps glyph strokes; on that clean raster we (1) OCR the
    page again and (2) re-read the located weight as one line (psm 7) at
    300/400/600 dpi. All reads feed the same ≥2-agreeing-reads vote.
    """
    from pathlib import Path as _P

    from invoice_extractor.ocr import is_ocr_backend

    texts: list[tuple[str, str]] = []
    tok: list[tuple[str, float]] = []
    notes: list[str] = []
    if not is_ocr_backend(backend) or not _P(path).is_file():
        return texts, tok, notes
    try:
        from invoice_extractor.ocr_reread import find_spans, page_words, reread_clip

        pw = page_words(path, dpi=300, clean_k=3)
        if not pw:
            return texts, tok, notes
        txt, words = pw
        texts.append(("clean", txt))
        spans = find_spans(words, _GW3_RX)
        if spans:
            # the weight is the first 3-group number below the SAID TO CONTAIN header
            raw, rect = min(spans, key=lambda sr: (sr[1][1], sr[1][0]))
            for dpi, t in reread_clip(path, rect, dpis=(300, 400, 600), whitelist="0123456789.,",
                                      clean_per_300dpi=3):
                v = _gw3(t)
                if v is not None:
                    tok.append((f"tok{dpi}", v))
            notes.append(f"GW token '{raw}' re-read (hatch removed): "
                         + (", ".join(f"{s}={v:g}" for s, v in tok) or "none"))
    except Exception as e:  # never break extraction on helper failure
        notes.append(f"clean re-read failed: {e}")
    return texts, tok, notes


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader()
    notes: list[str] = []
    ng: list[str] = []

    extra_texts, tok_gw, tok_notes = _clean_passes(path, backend)
    passes = [("r1", text)] + extra_texts

    nos = [n for _, t in passes for n in _bl_nos(t)]
    if nos:
        c = Counter(nos)
        (best, n), *rest = c.most_common()
        h.bl_no = best
        if rest and not (n >= 2 and n * 2 > len(nos)):
            ng.append("bl_no")
        if rest:
            notes.append(f"waybill no reads {dict(c)}")
    else:
        ng.append("bl_no")

    pk: list[tuple[str, float | None]] = []
    gw: list[tuple[str, float | None]] = []
    partial: list[str] = []
    for tag, t in passes:
        a, b, c_ = _pass_reads(t, tag)
        pk += a
        gw += b
        partial += c_
    gw += tok_gw

    # --- packages ---
    pkg, pkg_ok, pkg_detail = _vote(pk)
    h.packages = pkg
    if not pkg_ok:
        ng.append("packages")
    notes.append(f"pkg reads: {pkg_detail}")

    # --- GW ---
    g, gw_ok, gw_detail = _vote(gw)
    h.gross_weight_kg = g
    if not gw_ok:
        ng.append("gross_weight_kg")
    notes.append(f"GW reads: {gw_detail}")
    notes += tok_notes
    if partial and not gw_ok:
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
