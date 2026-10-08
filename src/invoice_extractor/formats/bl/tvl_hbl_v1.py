"""T.V.L. Global Logistics / Trans Van Links — HBL face (OCR-friendly).

BHC case7/8 scans: ``20260903091515-0001.pdf``, ``20260904232648-0001.pdf``.
B/L nos like ``SHAKEL########``; forwarder T.V.L. / TRANS VAN LINKS.
"""

from __future__ import annotations

import re

from invoice_extractor.schema import us_float
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta

MATCH_HINTS = {
    "filename_regex": r"2026\d+|SHAKEL|TVL",
    "keywords": [
        "T.V.L. GLOBAL LOGISTICS",
        "TRANS VAN LINKS",
        "BILL OF LADING",
        "SHAKEL",
        "FREIGHT COLLECT",
    ],
}

NOTES = (
    "TVL / Trans Van Links HBL face. Trained on OCR of BHC case7/8 scan HBLs "
    "(SHAKEL26970898 / SHAKEL26770270; BHC 3rd SHAKEL26971792 / SHAKEL26972017). "
    "Prefer cargo cartons/pallets over Say-Total container (1×20GP). "
    "GW/CBM: prefer CARTONS/KGS[/CBM] when carton count matches; 20GP CBM sanity ≤33; "
    "OCR slips (.830→.53, 46.519→16.519, GO.→CO.). "
    "Container: ISO 4 letters+7 digits + seal; invoice_refs: all BHCWH* / P/L NO. BHC 5th: SAY OCR ($1X→SIX, SAYTOTAL, em-dash); C/NO.…/N PALLET marks; slash-row GW preferred when pkg matches; uncorroborated multi-pass GW → needs_gold. Auditor 2026-10-05: the single face weight token and the B/L no are re-read as one line (psm 7) at 200/300/400 dpi and join the vote (page psm 6 swaps glyphs: 3185→3488, 1195.5→1498.5)."
)

RULES_JSON = {
    "id": "tvl_hbl_v1",
    "doc_kind": "hbl",
    "header": {
        "bl_no": r"B/L\s*NO\.?\s*(SHAKEL(?:\d{2}C\d{5}|\d+))",
        "packages": r"SAY\s+TOTAL[:\s]+(?:ONE\s*\(1\)\s*)?(\d+)?\s*(?:PALLET|20.?GP|CARTONS)",
        "gross_weight_kg": r"([\d,]+\.\d+)\s*K?GS",
    },
}


def match_score(text: str, filename: str = "") -> float:
    score = 0.0
    tu = text.upper()
    if "T.V.L" in tu or "TVL GLOBAL" in tu or "TRANS VAN LINKS" in tu:
        score += 0.45
    if re.search(r"SHAKEL\d+", tu) or _QDEX.search(text):
        score += 0.35
    if "BILL OF LADING" in tu:
        score += 0.1
    if "FREIGHT COLLECT" in tu:
        score += 0.05
    if "HIPPOPO" in tu or "CEVA LOGISTICS" in tu or "MILESTONE FORWARDING" in tu:
        score -= 0.5
    if "DHL GLOBAL FORWARDING" in tu:
        score -= 0.4
    return max(0.0, min(score, 1.0))


# TVL Qingdao office B/L no (BHC 3rd/4th case 3 photo ``QDEX2609096.jpg``);
# OCR reads D as b / p / B / O.
_QDEX = re.compile(r"(?<![A-Za-z0-9])Q[DdbpBO0]EX\s?(\d{7})(?!\d)")

_WORDS = {
    "ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5, "SIX": 6, "SEVEN": 7,
    "EIGHT": 8, "NINE": 9, "TEN": 10, "ELEVEN": 11, "TWELVE": 12, "THIRTEEN": 13,
    "FOURTEEN": 14, "FIFTEEN": 15, "SIXTEEN": 16, "SEVENTEEN": 17, "EIGHTEEN": 18,
    "NINETEEN": 19, "TWENTY": 20, "THIRTY": 30, "FORTY": 40, "FIFTY": 50,
    "SIXTY": 60, "SEVENTY": 70, "EIGHTY": 80, "NINETY": 90,
}
_UNIT = r"(?:PLYWOOD\s+|WOODEN\s+)?(?:PALLETS?|PACKAGES?|CARTONS?|PKGS|PLTS|CASES?|CRATES?)"
_DIGIT_FIX = str.maketrans({"O": "0", "o": "0", "T": "1", "I": "1", "l": "1", "|": "1",
                            "Z": "2", "z": "2", "S": "5", "B": "8"})


def _words_to_int(w: str) -> int | None:
    total, cur, seen = 0, 0, False
    for tok in re.split(r"[\s\-]+", w.upper().strip()):
        if not tok:
            continue
        if tok in _WORDS:
            cur += _WORDS[tok]
            seen = True
        elif tok == "HUNDRED" and seen:
            cur = max(cur, 1) * 100
        elif tok == "THOUSAND" and seen:
            total += max(cur, 1) * 1000
            cur = 0
        elif tok in ("AND",):
            continue
        else:
            return None
    return total + cur if seen else None


def _wnum(raw: str) -> float | None:
    """OCR weight token → float ("3612. 000", "7290,00", "21,690.00")."""
    t = re.sub(r"\s", "", raw)
    head_dec = re.match(r"^(.*[.,])([\dOo]{3})$", t)
    if head_dec:
        t = head_dec.group(1) + head_dec.group(2).replace("O", "0").replace("o", "0")
    if "," in t and "." in t:
        t = t.replace(",", "")
    elif "," in t:
        head, _, tail = t.rpartition(",")
        t = f"{head.replace(',', '')}.{tail}" if len(tail) in (2, 3) else t.replace(",", "")
    try:
        return float(t)
    except ValueError:
        return None


_ROW_RX = re.compile(
    r"(?<![A-Za-z0-9])([0-9OoTIlZzSB]{1,4})?\s*([CG]\s*ARTONS?|PACKAGES|PALLETS?|PLTS|PKGS)"
    r"\s*([/I!|,])\s*([\d,]+[.,]\s?\d{2,3})\s*K[GeE6][S53s]",
    re.I,
)
# face total weight; OCR may read the 3 decimals "000" as "OOO"
_FACE_GW_RX = re.compile(r"(?<![\d,.])(\d{1,3}(?:,?\d{3})*[.,]\s?[\dOo]{3})\s*K[GeE6][S53s]")


def _read_votes(text: str) -> dict:
    """One OCR pass → candidate reads for BL no / packages / GW (Result fields only)."""
    out: dict = {"bl_no": None, "say": [], "face_pkg": [], "rows": [], "face_gw": None}
    m = re.search(r"B/L\s*NO\.?\s*(SHAKEL\s?(?:\d{2}C\d{5,6}(?!\d)|\d+))", text, re.I) or re.search(
        r"\b(SHAKEL\s?(?:\d{2}C\d{5,6}|\d{8}))\b", text, re.I
    )
    if m:
        out["bl_no"] = re.sub(r"\s", "", m.group(1)).upper()
    else:
        q = _QDEX.search(text)
        if q:
            out["bl_no"] = f"QDEX{q.group(1)}"
    # SAY TOTAL: EIGHT (8) PALLETS / THIRTY PACKAGES (containers excluded).
    # OCR may glue SAYTOTAL, insert em-dashes, or mangle SIX→$1X / S1X.
    for sm in re.finditer(
        r"SAY\s*TOTAL\s*:?\s*([^\n]{0,40}?)\b(" + _UNIT + r")\b",
        text, re.I,
    ):
        if re.search(r"CONTAINER|\bGP\b|\bHC\b", sm.group(0), re.I):
            continue
        chunk = sm.group(1)
        # strip non-letters for word parse ($1X / — SIX / S1X)
        words_chunk = re.sub(r"[^A-Za-z\s\-]", " ", chunk)
        # common OCR: $1X / S1X / SlX / 5IX → SIX
        if re.search(r"(?:\$|S|5)\s*[lI1]\s*X\b", chunk, re.I) and not re.search(r"[A-Za-z]{3,}", words_chunk):
            words_chunk = "SIX"
        w = _words_to_int(words_chunk)
        if w:
            out["say"].append(("say_words", float(w)))
        dm = re.search(r"[({]\s*(\d{1,4})\s*[)}]", chunk)
        if dm:
            out["say"].append(("say_digits", float(dm.group(1))))
        break
    # Marks "C/NO.1-113/6 PALLET" (OCR CINO.1-143/6 PALLET) corroborates pkg
    for mm in re.finditer(
        r"(?:C\s*/?\s*NO\.?|CINO\.?)[^\n]{0,30}/\s*(\d{1,3})\s*PALLETS?\b",
        text, re.I,
    ):
        out["say"].append(("marks_slash", float(mm.group(1))))
        break
    # per-container rows "30CARTONS/7290.00KGS" ("!" = "/1", "I" = "/")
    row_spans = []
    for rm in _ROW_RX.finditer(text):
        cnt_raw = rm.group(1)
        cnt = None
        if cnt_raw:
            fixed = cnt_raw.translate(_DIGIT_FIX)
            if fixed.isdigit():
                cnt = float(int(fixed))
        wraw = rm.group(4)
        if rm.group(3) == "!":
            wraw = "1" + wraw
        out["rows"].append((cnt, _wnum(wraw)))
        row_spans.append(rm.span())
    # face total weight: first 3-dp KGS that is not a container row
    for fm in _FACE_GW_RX.finditer(text):
        if any(a <= fm.start() < b for a, b in row_spans):
            continue
        # a container row the row regex missed ("14PACKAGES ¢ 3448.000KGS / 25.450CBM")
        if re.match(r"\s*/\s*[\d.,\s]+C", text[fm.end():fm.end() + 20]) or re.search(
            r"(?:PACKAGES|CARTONS|PALLETS)\s*[^\w\s]?\s*$", text[max(0, fm.start() - 20):fm.start()], re.I
        ):
            continue
        out["face_gw"] = _wnum(fm.group(1))
        break
    # face package count under "No. of pkgs" ("(8 PALLETS", "190 CARTON" = "(90", "154 PKGS").
    # OCR often turns "/" into "!": "18 PALLETS ! 1 1498.500KGS" — still capture the count;
    # the leading "("→"1" slip is corrected later against SAY/marks votes.
    hm = re.search(r"No[.,]?\s*of\s*pkgs", text, re.I)
    if hm:
        tail = "\n".join(text[hm.end():].splitlines()[:4])
        fm = re.search(r"[(|‘'\s!]([0-9OoBZ]{1,4})\s*(" + _UNIT + r"|CARTON)\b", tail, re.I)
        if fm:
            fx = fm.group(1).translate(_DIGIT_FIX)
            if fx.isdigit():
                out["face_pkg"].append(int(fx))
    return out


def _second_read(path: str, backend: str) -> str | None:
    """Second OCR pass at a different resolution (scans only), for voting."""
    from pathlib import Path as _P

    from invoice_extractor.ocr import is_image_path, is_ocr_backend

    if not is_ocr_backend(backend):
        return None
    p = _P(path)
    if not p.is_file():
        return None
    try:
        if is_image_path(p):
            from invoice_extractor import ocr as _ocr
            import tempfile

            tess = _ocr.find_tesseract()
            if tess is None:
                return None
            with tempfile.TemporaryDirectory(prefix="tvl2_") as td:
                img = _ocr._prepare_image(p, _P(td), min_width=3000)
                return _ocr._run_tesseract(img, _P(td) / "o", lang=_ocr.DEFAULT_LANG, tess_bin=tess)
        from invoice_extractor.ocr import ocr_pdf

        text, _b = ocr_pdf(p, dpi=300)
        return text
    except Exception:
        return None


# Weight token on the face ("3185.000KGS", "1498.500 KGS") and B/L no token.
_TOK_GW_RX = re.compile(r"(?<![\d,.])\d[\d,.]*[.,]\s?[\dOo]{3}\s?K[GeE6][S53s]")
# Locator only (value is re-read): a face weight whose leading digits are mangled
# ("s7es2.000KG8" for 17652.000KGS, BHC 6th case5) — used when the strict token
# finds nothing.
_TOK_GW_LOOSE_RX = re.compile(r"(?<![\w,.])\S{0,4}\d[.,]\s?[\dOo]{3}\s?K[GeE6][S538s]?")
# Face package count under "No. of pkgs" ("71 CARTON", "60PACKAGES", "54 PKGS").
_TOK_PKG_WORD = re.compile(r"CART|PALLET|PACKAGE|PKG|PLT", re.I)
_TOK_BL_RX = re.compile(r"SHAKEL\s?\d{2}[0-9C]\d{3,6}|Q[DdbpBO0]EX\s?\d{7}")
# BHC 6th: TVL numbers with a letter in the 3rd place (SHAKEL26C72175 / SHAKEL26C71898).
# The single-line re-read may add a phantom glyph after the C ("26C072175").
_SHAKEL_C_PHANTOM = re.compile(r"SHAKEL(\d{2})C\d(\d{5})(?!\d)")


def _phantom_fix(tok_no: str, page_nos: list[str]) -> str:
    """``SHAKEL26C072175`` from the one-line re-read: drop the glyph after the C
    only when a page pass supports the 5-digit form (``SHAKEL26072175`` /
    ``SHAKEL26C72175``, same last 5 digits). A genuine 6-digit C number (page
    pass also has 6 digits after the C) is kept as read (Auditor round 2)."""
    m = _SHAKEL_C_PHANTOM.fullmatch(tok_no)
    if not m:
        return tok_no
    tail = m.group(2)
    if any(re.fullmatch(rf"SHAKEL{m.group(1)}[0-9C]{tail}", p) for p in page_nos):
        return f"SHAKEL{m.group(1)}C{tail}"
    return tok_no


def _token_reads(path: str, backend: str) -> dict:
    """Targeted re-reads of the face GW / B/L no (BHC 4th case1, 5th case1).

    The page pass (psm 6) on a thin 200-dpi bilevel scan swaps single glyphs
    in a clearly printed value (3185→3488/3485, 1195.5→1498.5, 269→268). We
    locate the value on a 200-dpi pass with word boxes and OCR only that clip
    as one line (psm 7, whitelist) at 200/300/400 dpi — three reads that go
    into the same vote as the page passes. GW re-reads are used only when the
    face shows exactly ONE weight token (a single total); container-row faces
    (several weights) keep the row-sum vote.
    """
    out: dict = {"gw": [], "bl_no": [], "pkg": [], "note": None}
    from pathlib import Path as _P

    from invoice_extractor.ocr import is_ocr_backend

    if not is_ocr_backend(backend) or not _P(path).is_file():
        return out
    try:
        from invoice_extractor.ocr_reread import find_spans, page_words, reread_clip

        pw = page_words(path, dpi=200)
        if not pw:
            return out
        _txt, words = pw
        gw_spans = find_spans(words, _TOK_GW_RX)
        if not gw_spans:
            gw_spans = find_spans(words, _TOK_GW_LOOSE_RX)
        if len(gw_spans) == 1:
            raw, rect = gw_spans[0]
            for dpi, t in reread_clip(path, rect, whitelist="0123456789.,KGS"):
                m = re.search(r"(\d[\d,.]*[.,]\d{3})\s*K?G?S?", t)
                v = _wnum(m.group(1)) if m else None
                if v is not None:
                    out["gw"].append((f"tok{dpi}", v))
            out["note"] = f"GW token '{raw}' re-read: " + (", ".join(f"{s}={v:g}" for s, v in out["gw"]) or "none")
        elif len(gw_spans) > 1:
            out["note"] = f"{len(gw_spans)} weight tokens on face (container rows) — no token re-read"
        out["pkg"] = _face_pkg_reads(path, words, find_spans, reread_clip)
        for raw, rect in find_spans(words, _TOK_BL_RX)[:1]:
            for dpi, t in reread_clip(path, rect, whitelist="SHAKELQDEXC0123456789",
                                      pad=(0.5, 0.5, 0.5, 0.5)):
                m = (
                    re.search(r"SHAKEL(\d{2}C\d{5,6}|\d{8})(?![\dC])", t)
                    or re.search(r"QDEX(\d{7})(?!\d)", t)
                )
                if m:
                    out["bl_no"].append((f"tok{dpi}", m.group(0)))
    except Exception as e:  # OCR helper failure never breaks extraction
        out["note"] = f"token re-read failed: {e}"
    return out


def _face_pkg_reads(path: str, words, find_spans, reread_clip) -> list[tuple[str, float]]:
    """Single-line re-reads of the face package count under ``No. of pkgs``
    (BHC 6th: ``71 CARTON`` OCR'd as ``iTHCARTON``; ``60PACKAGES`` as
    ``GOPACKAGES``; ``54 PKGS`` lost on the 300-dpi pass)."""
    hdr = find_spans(words, re.compile(r"No[.,]?\s*of\s*pkgs", re.I))
    if not hdr:
        return []
    hx0, hy0, hx1, hy1 = hdr[0][1]
    hh = max(1.0, hy1 - hy0)
    cands = [
        w for w in words
        if hy1 < w.y0 < hy1 + 8 * hh and _TOK_PKG_WORD.search(w.text)
        and w.x0 < hx1 + 4 * hh and w.x1 > hx0 - 6 * hh
    ]
    if not cands:
        return []
    cands.sort(key=lambda w: (w.y0, w.x0))
    unit = cands[0]
    same = [w for w in words if w.line == unit.line and w.x1 <= unit.x0 + 0.5 and unit.x0 - w.x1 < 3 * hh]
    x0 = min([unit.x0] + [w.x0 for w in same])
    rect = (x0, unit.y0, unit.x1, unit.y1)
    out: list[tuple[str, float]] = []
    for dpi, t in reread_clip(path, rect, whitelist="0123456789 ACEGKLNOPRST",
                              pad=(0.8, 0.4, 0.3, 0.4)):
        # the clip OCR still reads 6 as G / 0 as O ("GOPACKAGES" = 60PACKAGES)
        m = re.search(r"(?<![A-Z0-9])([0-9GOSBIZ]{1,4})\s*(CARTONS?|PALLETS?|PACKAGES?|PKGS?|PLTS?)\b", t)
        if m:
            fx = m.group(1).translate(_DIGIT_FIX).replace("G", "6")
            if fx.isdigit() and int(fx) > 0:
                out.append((f"tok{dpi}", float(fx)))
    return out


def _vote(reads: list[tuple[str, float]]) -> tuple[float | None, bool, str]:
    from collections import Counter

    vals = [v for _, v in reads if v is not None]
    detail = ", ".join(f"{s}={v:g}" for s, v in reads if v is not None) or "no reads"
    if not vals:
        return None, False, detail
    c = Counter(vals)
    (best, n), *rest = c.most_common()
    ok = n >= 2 and n * 2 > len(vals) and not (rest and rest[0][1] == n)
    return best, ok, detail


def _snip(s: str | None, n: int = 90) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n] if len(s) > n else s


def _ocr_company_suffix(s: str) -> str:
    """Light OCR fix: GO., LTD. → CO., LTD. (and similar company suffixes)."""
    s = re.sub(r"\bGO\.\s*,\s*LTD\b", "CO., LTD", s, flags=re.I)
    s = re.sub(r"\bGO\.\s*LTD\b", "CO. LTD", s, flags=re.I)
    s = re.sub(r"\bGO\.\s*,\s*LIMITED\b", "CO., LIMITED", s, flags=re.I)
    return s


def _ocr_seal_digits(seal: str) -> str:
    """In seal tokens, B/S often OCR-glitch for 8/5 amid digits (JJAA49B378→498378)."""
    out = []
    for ch in seal:
        if ch.upper() == "B" and (out and out[-1].isdigit()):
            out.append("8")
        elif ch.upper() == "S" and (out and out[-1].isdigit()) and len(out) >= 2:
            # only mid-digit S→5 when surrounded by digits context
            out.append("5")
        else:
            out.append(ch)
    return "".join(out)


def _normalize_bhc_ref(ref: str) -> str:
    """BHGWHQA… → BHCWHQA… (C→G OCR slip in BHCWH* family)."""
    r = ref.upper()
    # BHCWHYTW2609004 / BHCWHQA260915A (optional trailing letter)
    m = re.match(r"BH([A-Z])WH([A-Z]{2}\d+[A-Z]?)$", r)
    if m and m.group(1) != "C":
        return f"BHCWH{m.group(2)}"
    return r


def extract(path: str, text: str, backend: str, needs_ocr: bool) -> BLExtractResult:
    h = BLHeader(forwarder="T.V.L. Global Logistics Co., Ltd.")

    m = re.search(r"B/L\s*NO\.?\s*(SHAKEL(?:\d{2}C\d{5,6}(?!\d)|\d+))", text, re.I)
    if not m:
        m = re.search(r"\b(SHAKEL(?:\d{2}C\d{5,6}|\d+))\b", text, re.I)
    if m:
        h.bl_no = m.group(1).upper()
        h.hbl_no = h.bl_no
    else:
        q = _QDEX.search(text)
        if q:
            h.bl_no = f"QDEX{q.group(1)}"
            h.hbl_no = h.bl_no

    # Shipper: first company-like line after Shipper
    m = re.search(
        r"Shipper\s*\n\s*([A-Z][^\n]{5,80})",
        text,
        re.I,
    )
    if m:
        ship = re.sub(r"\s*B/L\s*NO\.?.*$", "", m.group(1), flags=re.I).strip(" ,")
        h.shipper = _snip(_ocr_company_suffix(ship))

    m = re.search(
        r"(?:ronsignee|Consignee|onsignee)\s*\n\s*([A-Z][^\n]{5,80})",
        text,
        re.I,
    )
    if m:
        h.consignee = _snip(_ocr_company_suffix(m.group(1)))

    m = re.search(
        r"Ocean Vessel[^\n]*\n\s*([A-Z][A-Z0-9 ,./-]{3,40})\s+V[.,]?\s*(\S+)",
        text,
        re.I,
    )
    if m:
        h.vessel = re.sub(r"\s+", " ", m.group(1)).strip(" ,")
        h.voyage = m.group(2).rstrip(",")

    m = re.search(r"Port of Loading\s*\n\s*([A-Z][^\n,]{2,40})", text, re.I)
    # Often vessel line includes POL — also search SHANGHAI / KEELUNG markers
    if re.search(r"SHANGHAI", text, re.I):
        h.pol = "SHANGHAI, CHINA"
    if re.search(r"KEELUNG", text, re.I):
        h.pod = "KEELUNG, TAIWAN"

    # Packages: prefer cargo cartons/pallets on the face, NOT Say-Total container
    # (e.g. "222 CARTONS" / "222CARTONS/2608.53KGS" wins over "SAY TOTAL: ONE (1) 20'GP").
    # Combo must not steal a leading letter digit (OCR "B26CARTONS" from "326").
    # Optional trailing /CBM (OCR may garble CBM as C5M / CBM)
    combo_rx = re.compile(
        r"(?<![A-Za-z0-9])(\d{1,4})\s*C\s*ARTONS\s*/\s*([\d]+[.,]\d{2,3})\s*K[G6][S5]?"
        r"(?:\s*/\s*([\d]+[.,]\d{2,3})\s*C[B5]?M)?",
        re.I,
    )
    combos = list(combo_rx.finditer(text))
    carton_counts = [
        float(m.group(1))
        for m in re.finditer(r"(?<![A-Za-z0-9])(\d{1,4})\s*CARTONS\b", text, re.I)
    ]
    m_plts = re.search(
        r"(?<![A-Za-z0-9])(\d{1,4})\s*CTNS?\s*=\s*(\d+)\s*PLTS?"
        r"|(?<![A-Za-z0-9])(\d{1,4})\s*PALLETS?\b",
        text,
        re.I,
    )

    if carton_counts:
        # Prefer the largest plausible face count (e.g. 326 over a stray 26).
        h.packages = max(carton_counts)
        h.package_unit = "CARTONS"
    elif combos:
        h.packages = float(combos[0].group(1))
        h.package_unit = "CARTONS"
    elif m_plts:
        # "83CTNS=2PLTS" → prefer CTNS group if present; else PALLETS count
        if m_plts.group(1) and m_plts.group(2):
            h.packages = float(m_plts.group(1))
            h.package_unit = "CARTONS"
        else:
            raw = m_plts.group(3) or m_plts.group(1)
            if raw:
                h.packages = float(raw)
                h.package_unit = "PALLETS"
    elif re.search(r"SAY\s+TOTAL[^\n]{0,40}PALLET|ONE\s*\(1\)\s*PALLET", text, re.I):
        h.packages = 1.0
        h.package_unit = "PALLET"
    elif re.search(r"SAY\s+TOTAL[^\n]{0,60}20.?GP|ONE\s*\(1\)\s*20", text, re.I):
        h.packages = 1.0
        h.package_unit = "20GP"

    # Gross weight: trust CARTONS/KGS combo only when its carton count matches
    # chosen packages; else use standalone KGS and fix common OCR .830↔.53 slips.
    def _to_f(raw: str) -> float | None:
        try:
            return float(raw.replace(",", "."))
        except ValueError:
            return None

    matched_combo_gw = None
    for cm in combos:
        if h.packages is not None and float(cm.group(1)) == float(h.packages):
            matched_combo_gw = _to_f(cm.group(2))
            if matched_combo_gw is not None:
                break
    if matched_combo_gw is not None:
        h.gross_weight_kg = matched_combo_gw
    else:
        weights_raw = re.findall(r"([\d]{2,5}[.,]\d{2,3})\s*K[G6][S5]?", text, re.I)
        # Drop combo weights whose carton count disagrees with packages
        mistrust = set()
        for cm in combos:
            if h.packages is None or float(cm.group(1)) != float(h.packages):
                mistrust.add(cm.group(2).replace(",", "."))
        cands = []
        for w in weights_raw:
            key = w.replace(",", ".")
            if key in mistrust:
                continue
            v = _to_f(w)
            if v is not None and 1 <= v <= 100000:
                cands.append((w, v))
        chosen_v = None
        if cands:
            # Prefer ###.### cargo face (3dp) over first 2dp when both exist,
            # unless the 3dp looks like the .830 OCR slip of a known .53 sibling.
            three = [(w, v) for w, v in cands if re.search(r"[.,]\d{3}$", w)]
            two = [(w, v) for w, v in cands if re.search(r"[.,]\d{2}$", w)]
            if three:
                w0, v0 = three[0]
                if str(v0).endswith("83") or w0.replace(",", ".").endswith("830"):
                    # 2608.830 vs face 2608.53 — prefer matching 2dp sibling
                    stem = int(v0)
                    sib = next((v for _, v in two if int(v) == stem), None)
                    if sib is not None:
                        chosen_v = sib
                    else:
                        # reconstruct common 5→8 OCR slip: *.830 → *.53
                        if w0.replace(",", ".").endswith("830"):
                            chosen_v = float(f"{stem}.53")
                        else:
                            chosen_v = v0
                else:
                    chosen_v = v0
            elif two:
                chosen_v = two[0][1]
        if chosen_v is not None:
            h.gross_weight_kg = chosen_v

    # Measurement CBM: prefer CARTONS/KGS/CBM combo matching packages; sanity vs 20GP (~33 max).
    matched_combo_cbm = None
    for cm in combos:
        if h.packages is not None and float(cm.group(1)) == float(h.packages) and cm.lastindex and cm.lastindex >= 3 and cm.group(3):
            matched_combo_cbm = _to_f(cm.group(3))
            if matched_combo_cbm is not None:
                break
    is_20gp = bool(re.search(r"20\s*['′]?\s*GP|\b20GP\b", text, re.I))
    cbm_cap = 33.0 if is_20gp else 70.0  # 40GP ~67; keep loose

    def _pick_cbm(cands: list[float]) -> float | None:
        if not cands:
            return None
        ok = [v for v in cands if 0.1 <= v <= cbm_cap]
        if ok:
            return ok[0]
        # OCR 1→4 on leading digit: 46.519 vs 16.519 — if v>cap try v-30
        for v in cands:
            if v > cbm_cap and (v - 30.0) <= cbm_cap and (v - 30.0) >= 0.1:
                return round(v - 30.0, 3)
        return cands[0] if cands[0] <= cbm_cap * 1.5 else None

    if matched_combo_cbm is not None:
        picked = _pick_cbm([matched_combo_cbm])
        if picked is not None:
            h.measurement_cbm = picked
    if h.measurement_cbm is None:
        # Standalone M3/CBM near cargo (avoid picking the OCR-glitched 46.519 when 16.519 exists)
        raws = re.findall(r"([\d]+[.,]\d{2,3})\s*(?:M3|C[B5]?M)\b", text, re.I)
        vals = []
        for r in raws:
            v = _to_f(r)
            if v is not None:
                vals.append(v)
        picked = _pick_cbm(vals)
        if picked is not None:
            h.measurement_cbm = picked

    # ISO container (4 letters + 7 digits) + optional seal / size from SAID TO CONTAIN line
    ctr_m = re.search(
        r"\b([A-Z]{4}\d{7})\s*/\s*([A-Z0-9]{4,12})\s*/\s*(20\s*['′]?\s*GP|40\s*['′]?\s*GP|20GP|40GP)",
        text,
        re.I,
    )
    if not ctr_m:
        ctr_m = re.search(r"\b([A-Z]{4}\d{7})\b", text, re.I)
    if ctr_m:
        ctr = ctr_m.group(1).upper()
        if ctr_m.lastindex and ctr_m.lastindex >= 2 and ctr_m.group(2):
            seal = _ocr_seal_digits(ctr_m.group(2).upper())
            size = re.sub(r"\s+", "", ctr_m.group(3).upper()) if ctr_m.lastindex >= 3 and ctr_m.group(3) else None
            h.container_nos = f"{ctr} / {seal}" + (f" / {size}" if size else "")
        else:
            h.container_nos = ctr
        if is_20gp and not h.package_unit:
            pass  # keep cargo unit; load_type optional
        if is_20gp:
            h.load_type = h.load_type or "FCL"

    # Invoice / PL refs — capture all BHCWH* (incl. slash list) and P/L / PIL NO lines
    refs: list[str] = []
    for mm in re.finditer(
        r"P[/I]?\s*L\s*NO[:\s]*([A-Z0-9_\-/]+)",
        text,
        re.I,
    ):
        chunk = mm.group(1)
        for part in re.split(r"[/]", chunk):
            part = part.strip(" ,;")
            if re.match(r"^[A-Z0-9_-]{6,}$", part, re.I):
                refs.append(_normalize_bhc_ref(part))
    for mm in re.finditer(r"\b(BH[A-Z]?WH[A-Z]{2}\d+)\b", text, re.I):
        refs.append(_normalize_bhc_ref(mm.group(1)))
    for mm in re.finditer(r"\b(NBT\d+)\b", text, re.I):
        refs.append(mm.group(1).upper())
    if refs:
        h.invoice_refs = ", ".join(dict.fromkeys(refs))

    # ---- BHC 4th: vote BL no / packages / GW over two OCR passes ---------
    # (per-container breakdown sums, SAY TOTAL words+digits, face total) so a
    # single misread (3488 vs 3185, 190 vs 90 CARTON, container count as pkg)
    # is either outvoted or flagged needs_gold instead of passing silently.
    ng: list[str] = []
    vnotes: list[str] = []
    passes = [("r1", text)]
    t2 = _second_read(path, backend)
    if t2:
        passes.append(("r2", t2))
    reads = [(tag, _read_votes(t)) for tag, t in passes]
    # targeted single-line re-reads of the face GW / B/L no (scans only)
    tok = _token_reads(path, backend)
    if tok.get("note"):
        vnotes.append(tok["note"])

    # BL no
    from collections import Counter as _C
    from pathlib import Path as _P

    fn = _P(path).stem.upper()
    page_nos = [(tag, r["bl_no"]) for tag, r in reads if r["bl_no"]]
    nos = page_nos + [(t, _phantom_fix(n, [p for _, p in page_nos])) for t, n in tok["bl_no"]]
    uniq = list(dict.fromkeys(n for _, n in nos))
    if len(uniq) > 1:
        (top, n_top), *rest_no = _C(n for _, n in nos).most_common()
        pick = next((n for n in uniq if n in fn), None)
        if pick is None and n_top >= 2 and n_top * 2 > len(nos) and not (rest_no and rest_no[0][1] == n_top):
            pick = top  # clear majority incl. token re-reads → no needs_gold
        if pick is None:
            pick = nos[-1][1]  # higher-resolution pass
            ng.append("bl_no")
        h.bl_no = h.hbl_no = pick
        vnotes.append("bl_no reads " + ", ".join(f"{t}={n}" for t, n in nos))
    elif uniq and not h.bl_no:
        h.bl_no = h.hbl_no = uniq[0]

    face_gws = [r["face_gw"] for _, r in reads if r["face_gw"] is not None]
    gw_reads: list[tuple[str, float]] = [(f"face_{t}", r["face_gw"]) for t, r in reads if r["face_gw"] is not None]
    # token re-reads of the single face weight: consensus = ≥2 agreeing, strict majority
    tok_gw = list(tok["gw"])
    tok_best, tok_ok, _ = _vote(tok_gw)
    if not tok_ok:
        tok_best = None
    gw_reads += tok_gw
    pkg_reads: list[tuple[str, float]] = []
    for t, r in reads:
        pkg_reads += [(f"{k}_{t}", v) for k, v in r["say"]]
        rows = r["rows"]
        if rows and all(w is not None for _, w in rows):
            wsum = round(sum(w for _, w in rows), 3)
            # rows must add up to a face total (tolerance 1.0), OR a lone slash
            # row is kept even when face disagrees by a few kg (OCR digit slip
            # e.g. 13101 vs 13104) so the vote / needs_gold can decide.
            close = any(abs(wsum - f) <= 1.0 for f in face_gws)
            lone = len(rows) == 1
            if close or lone:
                gw_reads.append((f"rows_{t}", wsum))
                if all(c is not None for c, _ in rows):
                    pkg_reads.append((f"rows_{t}", float(sum(c for c, _ in rows))))
    # face package count re-read as one line (needs ≥2 agreeing clip reads)
    tok_pkg = list(tok.get("pkg") or [])
    if tok_pkg:
        tb, tok_pok, _ = _vote(tok_pkg)
        # the clip re-reads the FACE count only: it may corroborate a SAY /
        # slash-row read or stand in when there is none, but never outvote a
        # SAY total (BHC 5th case1: face "18 PALLETS" vs SAY SIX (6)).
        if tok_pok and (not pkg_reads or tb in {v for _, v in pkg_reads}):
            pkg_reads += tok_pkg
    others = {v for _, v in pkg_reads}
    for t, r in reads:
        for fp in r["face_pkg"]:
            v = float(fp)
            s_fp = str(fp)
            # leading "(" often OCRs as "1": 190 CARTON → 90, 154 PKGS → 54
            if v not in others and len(s_fp) >= 2 and s_fp[0] == "1" and float(s_fp[1:]) in others:
                v = float(s_fp[1:])
            pkg_reads.append((f"face_{t}", v))

    pv, pok, pdetail = _vote(pkg_reads)
    if pok:
        if h.packages != pv:
            vnotes.append(f"pkg {pv:g} by vote (legacy {h.packages})")
        h.packages = pv
    elif pkg_reads and pv is not None and (pv != h.packages or "bl_no" in ng):
        ng.append("packages")
        h.packages = pv if h.packages in (None, 1.0) else h.packages
    # Prefer slash-row GW whose package count matches the voted packages
    # (31PALLETS/13101 over face 13104).
    if pok and pv is not None:
        matched_row_gws = []
        for t, r in reads:
            for cnt, w in r["rows"]:
                if cnt is not None and w is not None and float(cnt) == float(pv):
                    matched_row_gws.append(w)
        if tok_best is not None and matched_row_gws and any(abs(w - tok_best) > 1.0 for w in matched_row_gws):
            # the slash row IS the face weight; its page read lost to the clip re-reads
            vnotes.append(f"slash row GW {matched_row_gws} overruled by token re-reads {tok_best:g}")
            matched_row_gws = []
        if matched_row_gws and len(set(matched_row_gws)) == 1:
            gv_pref = matched_row_gws[0]
            if h.gross_weight_kg != gv_pref:
                vnotes.append(f"GW {gv_pref:g} by slash row matching pkg {pv:g}")
            h.gross_weight_kg = gv_pref
            # drop disagreeing face-only reads so vote reflects the slash
            gw_reads = [(s, v) for s, v in gw_reads if not s.startswith("face_") or abs(v - gv_pref) <= 1.0]
            if not any(s.startswith("rows_") for s, _ in gw_reads):
                gw_reads.append(("rows_pref", gv_pref))

    gv, gok, gdetail = _vote(gw_reads)
    if gok:
        h.gross_weight_kg = gv
    elif len({v for _, v in gw_reads}) > 1 or (gw_reads and "bl_no" in ng) or (
        gw_reads and not gok and len(passes) > 1
    ):
        # reads disagree, BL no unreliable, or a multi-pass scan with no
        # corroborated GW (single face misread e.g. 1498.5 vs real 1195.5)
        # → needs_gold (suggested value kept)
        if "gross_weight_kg" not in ng:
            ng.append("gross_weight_kg")
    if h.gross_weight_kg is None and gv is not None:
        h.gross_weight_kg = gv  # suggested (needs_gold below)
    if len(passes) > 1:
        # scanned face with no usable read at all → value is missing, flag it
        if h.packages is None and "packages" not in ng:
            ng.append("packages")
        if h.gross_weight_kg is None and "gross_weight_kg" not in ng:
            ng.append("gross_weight_kg")
    vnotes.append(f"pkg reads: {pdetail}")
    vnotes.append(f"GW reads: {gdetail}")

    conf = "rules"
    needs_gold = False
    if not h.bl_no:
        conf = "needs_gold"
        needs_gold = True
        if "bl_no" not in ng:
            ng.append("bl_no")
    if ng:
        conf = "needs_gold"
        needs_gold = True

    base_note = NOTES if conf == "rules" else "TVL HBL partial"
    if ng:
        base_note = "needs_gold: " + ", ".join(ng) + " (OCR reads disagree / too few); " + base_note
    return BLExtractResult(
        header=h,
        meta=BLMeta(
            source_file=path,
            text_backend=backend,
            format_id="tvl_hbl_v1",
            confidence=conf,
            needs_ocr=needs_ocr,
            needs_gold=needs_gold,
            needs_gold_fields=ng or None,
            doc_kind="hbl",
            notes=base_note + "; " + "; ".join(vnotes),
        ),
    )
