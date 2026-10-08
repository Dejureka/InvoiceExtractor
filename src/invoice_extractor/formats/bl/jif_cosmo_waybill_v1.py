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


_KEE_SPAN = re.compile(r"\d[\dOo ]{3,8}\s?K\s?E\s?E|KEE\s?\d", re.I)
_GW_HDR = re.compile(r"Gross\s*We\w*", re.I)
_INV_SPAN = re.compile(r"[I1l]?N[VY][O0]\w{0,4}\s*N[O0]", re.I)
_FACE = re.compile(r"Gross\s*We|Measurement|Waybill\s*No|NON-?NEGOTIABLE", re.I)
# one trailing digit after the 3 decimals is a hatch fragment (``50.0005``)
_CELL_GW = re.compile(r"(\d{1,3}(?:[,.]\s?\d{3})*)[.,]\s?(\d{3})(?!\d{2})")


def _gw_cell(s: str) -> float | None:
    """Weight from a single-cell re-read. JIFFA weights always print 3 decimals
    (``50.000``, ``1,774.500``): the last 3-digit group is the decimals."""
    best = None
    for m in _CELL_GW.finditer(s.replace(" ", "")):
        if best is None or len(m.group(0)) > len(best.group(0)):
            best = m
    if best is None:
        return None
    ip = re.sub(r"[,.]", "", best.group(1))
    v = round(int(ip) + int(best.group(2)) / 1000, 3)
    return v if v > 0 else None


_DIGITS2 = re.compile(r"\d.*\d")


def _component_vote(comps: list[tuple[int, float]]) -> tuple[float | None, int]:
    """Vote integer part and decimals of the cell reads separately (hatch noise
    hits one digit group at a time: ``50.006`` / ``40.000`` → 50 / .000).
    Each part needs ≥2 agreeing reads and a strict majority of the reads."""
    if not comps:
        return None, 0
    (ip, ni), = Counter(i for i, _ in comps).most_common(1)
    (dp, nd), = Counter(d for _, d in comps).most_common(1)
    if ni < 2 or nd < 2 or ni * 2 <= len(comps) or nd * 2 <= len(comps):
        return None, 0
    return round(ip + dp, 3), min(ni, nd)


def _gw_cell_rect(path: str, page: int, words, hdr_rect) -> tuple | None:
    """Box of the first weight under the ``Gross Weight`` header.

    The hatch stamp merges fragments into the number's OCR word (``S745,``,
    ``60.00]``, ``48,000"``) or hides it, differently per cleaning. Each of the
    page passes (raw, hatch-removed k=3 / k=4) gives the topmost digit word(s)
    in the header's column; the common part of those boxes is the number
    itself, without the hatch fragments next to it.
    """
    from invoice_extractor.ocr_reread import page_words

    hx0, hy0, hx1, hy1 = hdr_rect
    h = max(1.0, hy1 - hy0)

    def row_box(ws):
        cand = [w for w in ws if _DIGITS2.search(w.text) and w.x1 > hx0 - 1.5 * h and w.x0 < hx1 + 0.5 * h
                and hy1 + 0.8 * h < w.y0 < hy1 + 7 * h]
        if not cand:
            return None
        top = min(cand, key=lambda w: w.y0)
        # same line: every word with a digit (the ``3,`` of ``3, 084, 500`` too)
        row = [w for w in ws if any(ch.isdigit() for ch in w.text) and w.y0 < top.y1 and w.y1 > top.y0
               and w.x1 > hx0 - 1.5 * h and w.x0 < hx1 + 0.5 * h]
        return (min(w.x0 for w in row), min(w.y0 for w in row),
                min(max(w.x1 for w in row), hx1 + 0.5 * h), max(w.y1 for w in row))

    boxes = [b for b in (row_box(words),) if b]
    for k in (0, 4):
        pw = page_words(path, dpi=300, page=page, clean_k=k)
        if pw:
            b = row_box(pw[1])
            if b:
                boxes.append(b)
    if not boxes:
        return None
    if len(boxes) == 1:
        return boxes[0]
    r = (max(b[0] for b in boxes), max(b[1] for b in boxes), min(b[2] for b in boxes), min(b[3] for b in boxes))
    if r[2] - r[0] < 2 * h or r[3] - r[1] < 0.4 * h:  # passes disagree on where the number is
        return None
    return r


def _located_reads(path: str, page: int, words, want_inv: bool) -> dict:
    """Regional re-reads located on one page (BHC 6th round 2, Auditor 2026-10-08):

    * waybill no — the ``…KEE…`` token, one text line high, bottom-anchored
      (the OCR box can merge with the label above);
    * GW — the cell under the ``Gross Weight`` header (row of the first cargo
      line, under ``(KGS)``), re-read as one word with and without hatch removal;
      on the hatch stamp the page pass finds no number at all (case8 50.000);
    * invoice no — the ``INVOICE NO.…`` line in the goods description (only
      for multi-waybill PDFs, to pick the waybill of the paired invoice).
    Each zoom × cleaning is one read for the ≥2-agreeing-reads votes.
    """
    from invoice_extractor.ocr_reread import find_spans, line_height, line_run, page_words, reread_clip

    out: dict = {"bl": [], "gw": [], "inv": [], "notes": []}
    lh = line_height(words)
    for raw, (x0, y0, x1, y1) in find_spans(words, _KEE_SPAN)[:2]:
        rect = (x0, y1 - lh, max(x1, x0 + 5 * lh) + 3.5 * lh, y1)
        for cl in (0, 3):
            for dpi, t in reread_clip(path, rect, page=page, dpis=(300, 400, 600), whitelist="0123456789KE",
                                      pad=(0.3, 0.25, 0.3, 0.25), clean_per_300dpi=cl):
                m = re.search(r"(?<!\d)(\d{6})KEE(\d{3})(?!\d)", t)
                if m:
                    out["bl"].append((f"tok{dpi}c{cl}", f"{m.group(1)}KEE{m.group(2)}"))
    hdr = find_spans(words, _GW_HDR)
    if hdr:
        rect = _gw_cell_rect(path, page, words, hdr[0][1])
        if rect is None:
            out["notes"].append("GW cell: no number located under the Gross Weight header")
        else:
            raws, comps = [], []
            for cl in (0, 2, 3, 4):
                for dpi, t in reread_clip(path, rect, page=page, dpis=(300, 400, 600), whitelist="0123456789.,",
                                          pad=(0.3, 0.4, 0.1, 0.4), clean_per_300dpi=cl, psm="8"):
                    v = _gw_cell(t)
                    raws.append(f"{dpi}c{cl}={v:g}" if v is not None else f"{dpi}c{cl}=-")
                    if v is not None:
                        comps.append((int(v), round(v - int(v), 3)))
            v, n = _component_vote(comps)
            note = (f"GW cell {tuple(round(x) for x in rect)} re-read: " + ", ".join(raws)
                    + (f" → integer/decimals vote {v:g} ({n} of {len(raws)})" if v is not None else " → no majority"))
            if v is not None:
                # whole-number check: the same vote on a box widened into the
                # neighbouring cell space must give the same value; a box that cut
                # off a leading ``1,`` (774.5 of 1,774.5) or the decimals (1,774
                # → 1.774) reads differently once widened
                hx0, hy0, hx1, hy1 = hdr[0][1]
                h = max(1.0, hy1 - hy0)
                wide = (max(rect[0] - 1.5 * h, hx0 - 1.5 * h), rect[1],
                        min(rect[2] + 2.5 * h, hx1 + 1.0 * h), rect[3])
                wcomps, wraws = [], []
                for cl in (0, 2, 3, 4):
                    for dpi, t in reread_clip(path, wide, page=page, dpis=(300, 400, 600),
                                              whitelist="0123456789.,", pad=(0.3, 0.4, 0.1, 0.4),
                                              clean_per_300dpi=cl, psm="8"):
                        wv = _gw_cell(t)
                        wraws.append(f"{wv:g}" if wv is not None else "-")
                        if wv is not None:
                            wcomps.append((int(wv), round(wv - int(wv), 3)))
                wv, wn = _component_vote(wcomps)
                verified = wv is not None and abs(wv - v) < 1e-6
                out["gw_cell"] = {"value": v, "verified": verified}
                note += (f"; widened box {tuple(round(x) for x in wide)}: " + ", ".join(wraws)
                         + (f" → {wv:g}" if wv is not None else " → no majority")
                         + (" — whole number confirmed" if verified else " — NOT confirmed (cell may be truncated)"))
            out["notes"].append(note)
    if want_inv:
        spans = find_spans(words, _INV_SPAN)
        iw = words
        if not spans:
            pw = page_words(path, dpi=400, page=page, clean_k=7)
            if pw:
                iw = pw[1]
                spans = find_spans(iw, _INV_SPAN)
        ilh = line_height(iw)
        for raw, r in spans[:3]:
            x0, y0, x1, y1 = line_run(iw, r, max_gap=2.5 * ilh, max_width=16 * ilh)
            x1 = max(x1, x0 + 12 * ilh)
            for cl in (0, 3):
                for dpi, t in reread_clip(path, (x0, y0, x1, y1), page=page, dpis=(300, 400, 600),
                                          whitelist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,-:",
                                          pad=(0.4, 0.3, 0.4, 0.3), clean_per_300dpi=cl):
                    m = re.search(r"N[O0]\s*[.,:]?\s*([A-Z0-9][A-Z0-9\-]{3,19})", t)
                    if m:
                        out["inv"].append(m.group(1))
    return out


def _clean_passes(path: str, backend: str, page: int = 0, want_inv: bool = False):
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
    loc: dict = {"bl": [], "gw": [], "inv": [], "notes": []}
    if not is_ocr_backend(backend) or not _P(path).is_file():
        return texts, tok, notes, loc
    try:
        from invoice_extractor.ocr_reread import find_spans, page_words, reread_clip

        pw = page_words(path, dpi=300, page=page, clean_k=3)
        if not pw:
            return texts, tok, notes, loc
        txt, words = pw
        texts.append(("clean", txt))
        spans = find_spans(words, _GW3_RX)
        if spans:
            # the weight is the first 3-group number below the SAID TO CONTAIN header
            raw, rect = min(spans, key=lambda sr: (sr[1][1], sr[1][0]))
            for dpi, t in reread_clip(path, rect, page=page, dpis=(300, 400, 600), whitelist="0123456789.,",
                                      clean_per_300dpi=3):
                v = _gw3(t)
                if v is not None:
                    tok.append((f"tok{dpi}", v))
            notes.append(f"GW token '{raw}' re-read (hatch removed): "
                         + (", ".join(f"{s}={v:g}" for s, v in tok) or "none"))
        loc = _located_reads(path, page, words, want_inv)
    except Exception as e:  # never break extraction on helper failure
        notes.append(f"clean re-read failed: {e}")
    return texts, tok, notes, loc


def _source_value(reads: list[float]) -> float | None:
    """One source = one vote: the strict-majority value of that source's own
    reads (re-reads of one clip at several dpi / cleanings are correlated);
    no strict majority → the source abstains."""
    if not reads:
        return None
    (v, n), = Counter(reads).most_common(1)
    return v if n * 2 > len(reads) else None


def _decide_gw(sources: list[tuple[str, float | None]], cell: dict | None):
    """Conservative GW decision (Auditor round 4, 2026-10-08).

    ``sources``: one vote per independent source — each page pass (r1, clean)
    and the token clip (its 3 dpi re-reads collapsed to one value). The located
    cell (12 re-reads collapsed by the integer/decimals vote) is a source only
    when the widened-box check confirmed it; an unconfirmed cell never votes.

    * Confident only with ≥2 voting sources that ALL agree, and no cell value
      (confirmed or not) disagreeing. Any disagreement → needs_gold (value kept
      as a suggestion). An unconfirmed cell never counts towards the ≥2, so it
      can never decide; it can only block.
    * Cell only (no page/token source): never decided here — needs_gold, and
      ``gw_cell_only`` lets the batch step accept it only when it equals the
      INV/PL G.W. total of all invoices sharing this waybill.

    Returns ``(value, confident, detail, note, gw_cell_only_value)``.
    """
    srcs = [(t, v) for t, v in sources if v is not None]
    cv = (cell or {}).get("value")
    confirmed = bool((cell or {}).get("verified"))
    if not srcs:
        if cv is None:
            return None, False, "no reads", None, None
        return cv, False, f"cell={cv:g} (cell only)", (
            f"GW {cv:g} from the cell re-read only → needs_gold unless it equals the INV/PL G.W. total of the "
            f"invoices on this waybill"), cv
    votes = srcs + ([("cell", cv)] if cv is not None and confirmed else [])
    detail = ", ".join(f"{t}={v:g}" for t, v in votes)
    if cv is not None and not confirmed:
        detail += f" (cell {cv:g} unconfirmed, not voting)"
    (best, n), *rest = Counter(v for _, v in votes).most_common()
    # clean = ≥2 voting sources, all agreeing, and the cell (confirmed or not)
    # does not disagree; anything else → needs_gold
    ok = n >= 2 and not rest and (cv is None or cv == best)
    note = None
    if cv is not None and cv != best:
        note = f"GW cell {cv:g} ({'confirmed' if confirmed else 'unconfirmed'}) disagrees with {best:g} → needs_gold"
    return best, ok, detail, note, None


def _read_waybill(path: str, backend: str, page: int, text: str, want_inv: bool) -> dict:
    """All votes for one waybill face (``page``) + its attached sheet text."""
    notes: list[str] = []
    ng: list[str] = []
    extra_texts, tok_gw, tok_notes, loc = _clean_passes(path, backend, page, want_inv)
    passes = [("r1", text)] + extra_texts

    nos = [("page", n) for _, t in passes for n in _bl_nos(t)] + list(loc["bl"])
    bl_no = None
    if nos:
        c = Counter(n for _, n in nos)
        (best, n), *rest = c.most_common()
        bl_no = best
        if rest and not (n >= 2 and n * 2 > len(nos)):
            ng.append("bl_no")
        if rest:
            notes.append(f"waybill no reads {dict(c)}")
    else:
        ng.append("bl_no")

    pk: list[tuple[str, float | None]] = []
    sources: list[tuple[str, float | None]] = []
    partial: list[str] = []
    for tag, t in passes:
        a, b, c_ = _pass_reads(t, tag)
        pk += a
        partial += c_
        sources.append((tag, _source_value([v for _, v in b if v is not None])))
    sources.append(("tok", _source_value([v for _, v in tok_gw if v is not None])))
    pkg, pkg_ok, pkg_detail = _vote(pk)
    if not pkg_ok:
        ng.append("packages")
    notes.append(f"pkg reads: {pkg_detail}")
    g, gw_ok, gw_detail, gw_note, cell_only = _decide_gw(sources, loc.get("gw_cell"))
    if not gw_ok:
        ng.append("gross_weight_kg")
    notes.append(f"GW reads: {gw_detail}")
    if gw_note:
        notes.append(gw_note)
    notes += tok_notes + loc["notes"]
    if partial and not gw_ok:
        notes.append(f"GW partial OCR read(s) {partial} (incomplete — digits lost under the background pattern)")
    return {"bl_no": bl_no, "packages": pkg, "gross_weight_kg": g, "needs_gold_fields": ng,
            "invoice_reads": list(loc["inv"]), "notes": notes, "gw_cell_only": cell_only}


def _waybill_groups(text: str) -> list[tuple[int, list[int]]]:
    """Face pages (``Gross Weight`` / ``Waybill No.`` header) and the pages that
    follow each one (attached marks sheet) → ``[(face_index, [page indexes])]``."""
    pages = text.split("\f")
    groups: list[tuple[int, list[int]]] = []
    for i, t in enumerate(pages):
        if _FACE.search(t) or not groups:
            groups.append((i, [i]))
        else:
            groups[-1][1].append(i)
    return groups


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader()
    pages = text.split("\f")
    groups = _waybill_groups(text)
    docs = []
    distinct: set = set()
    if len(groups) > 1:
        for face, idx in groups:
            r = _read_waybill(path, backend, face, "\n".join(pages[i] for i in idx), want_inv=True)
            r["pages"] = [i + 1 for i in idx]
            docs.append(r)
        distinct = {d["bl_no"] for d in docs if d["bl_no"]}
    if len(groups) > 1 and len(distinct) > 1:
        # Several waybills in one forwarder scan (BHC 6th case8: KEE601 p1–2 +
        # KEE602 p3). Standalone the file cannot say which one is meant →
        # needs_gold; pairing picks the waybill whose printed INVOICE NO. matches
        # the invoice (``pairing.select_bl_document``).
        ng = ["bl_no", "packages", "gross_weight_kg"]
        def _pg(d):
            p = d["pages"]
            return f"p{p[0]}" if len(p) == 1 else f"p{p[0]}-{p[-1]}"

        lst = "; ".join(f"{_pg(d)} {d['bl_no']} (INVOICE NO. reads {sorted(set(d['invoice_reads']))[:4]})" for d in docs)
        notes = [f"needs_gold: bl_no, packages, gross_weight_kg ({len(docs)} waybills in one PDF: {lst}; "
                 f"selected by the paired invoice no.)"]
        return BLExtractResult(
            header=h,
            meta=BLMeta(
                source_file=path,
                text_backend=backend,
                format_id="jif_cosmo_waybill_v1",
                confidence="needs_gold",
                needs_ocr=needs_ocr,
                needs_gold=True,
                needs_gold_fields=ng,
                notes="; ".join(notes),
                doc_kind="sea_waybill",
                documents=[
                    {"pages": d["pages"], "bl_no": d["bl_no"], "packages": d["packages"],
                     "gross_weight_kg": d["gross_weight_kg"], "needs_gold_fields": d["needs_gold_fields"] or None,
                     "invoice_reads": d["invoice_reads"], "notes": "; ".join(d["notes"]),
                     "gw_cell_only": d["gw_cell_only"]}
                    for d in docs
                ],
            ),
        )

    face = groups[0][0] if groups else 0
    r = _read_waybill(path, backend, face, text, want_inv=False)
    h.bl_no, h.packages, h.gross_weight_kg = r["bl_no"], r["packages"], r["gross_weight_kg"]
    ng = r["needs_gold_fields"]
    notes = r["notes"]
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
            gw_cell_only=r["gw_cell_only"],
        ),
    )
