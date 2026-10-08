"""Targeted OCR re-reads of one printed value (BL GW / BL no) on a scan.

Why (BHC 4th case1 / case6, BHC 5th case1, Auditor 2026-10-05): a full-page
Tesseract pass (``--psm 6``) on a thin 200-dpi bilevel scan misreads single
glyphs in an otherwise clear number (``3185.000KGS`` → ``3488,000KGS`` /
``3485,000KGS``; ``1195.500KGS`` → ``1498.500KGS``), and on the JIFFA
anti-counterfeit background it loses the thousands group (``998, 000``). The
page pass then gives one uncorroborated read and the value was either kept
wrong as a suggestion or left blank.

Two tools, pymupdf + tesseract only (no numpy / PIL in the portable build):

* :func:`page_words` – one page pass with word boxes (TSV), optionally after
  :func:`remove_hlines` (vertical opening that drops 1–2 px horizontal hatch
  lines but keeps glyph strokes).
* :func:`reread_clip` – render just the located value at several zooms and
  OCR it as a single text line (``--psm 7``, character whitelist). Each zoom
  is one independent read for the caller's ≥2-agreeing-reads vote.

Result fields only — callers use this for BL No. / BL Packages / BL G.W.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from invoice_extractor import ocr as _ocr


@dataclass
class Word:
    text: str
    x0: float  # PDF points (page coordinates)
    y0: float
    x1: float
    y1: float
    line: tuple


def _run(cmd: list[str], tess: Path) -> str:
    proc = subprocess.run(
        cmd, capture_output=True, text=True, env=_ocr._tesseract_env(tess), timeout=120, check=False
    )
    return proc.stdout or ""


def remove_hlines(pix, k: int):
    """Return a grayscale pixmap keeping only ink with a vertical run ≥ ``k`` px.

    Rows are packed as Python big ints (1 bit per pixel) so the vertical
    erosion + dilation is a few thousand int AND/OR ops per page.
    """
    import pymupdf

    if pix.n != 1 or pix.alpha:
        pix = pymupdf.Pixmap(pymupdf.csGRAY, pix)
    w, h, stride = pix.width, pix.height, pix.stride
    data = pix.samples
    to01 = bytes((49 if v < 128 else 48) for v in range(256))  # ink → '1'
    rows = [int(data[y * stride:y * stride + w].translate(to01), 2) for y in range(h)]
    k = max(1, int(k))
    er = [0] * h
    for y in range(h - k + 1):
        v = rows[y]
        for d in range(1, k):
            v &= rows[y + d]
            if not v:
                break
        er[y] = v
    out = bytearray()
    back = bytes.maketrans(b"01", b"\xff\x00")
    for y in range(h):
        v = 0
        for d in range(k):
            if y - d >= 0:
                v |= er[y - d]
        out += format(v, f"0{w}b").encode().translate(back) if v else b"\xff" * w
    return pymupdf.Pixmap(pymupdf.csGRAY, w, h, bytes(out), 0)


def _render(doc, page_no: int, dpi: int, clip=None, clean_k: int = 0):
    import pymupdf

    page = doc[page_no]
    z = dpi / 72.0
    pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), clip=clip, alpha=False, colorspace=pymupdf.csGRAY)
    if clean_k:
        pix = remove_hlines(pix, clean_k)
    return pix


def page_words(path: str | Path, *, dpi: int = 200, page: int = 0, clean_k: int = 0,
               lang: str = _ocr.DEFAULT_LANG, min_width_px: int = 1600) -> tuple[str, list[Word]] | None:
    """One OCR pass of ``page`` → (text, words with boxes in PDF points).

    Small phone photos (image docs report a tiny page in points) are zoomed so
    the raster is at least ``min_width_px`` wide.
    """
    import pymupdf

    tess = _ocr.find_tesseract()
    p = Path(path)
    if tess is None or not p.is_file():
        return None
    doc = pymupdf.open(p)
    try:
        if page >= len(doc):
            return None
        dpi = max(dpi, int(min_width_px * 72.0 / max(1.0, doc[page].rect.width)) + 1)
        pix = _render(doc, page, dpi, clean_k=clean_k)
        with tempfile.TemporaryDirectory(prefix="rr_") as td:
            img = Path(td) / "p.png"
            pix.save(str(img))
            base = Path(td) / "o"
            subprocess.run(
                [str(tess), str(img), str(base), "-l", lang, "--psm", "6", "txt", "tsv"],
                capture_output=True, text=True, env=_ocr._tesseract_env(tess), timeout=180, check=False,
            )
            txt = (base.with_suffix(".txt")).read_text(encoding="utf-8", errors="replace") if base.with_suffix(".txt").is_file() else ""
            tsv = (base.with_suffix(".tsv")).read_text(encoding="utf-8", errors="replace") if base.with_suffix(".tsv").is_file() else ""
    finally:
        doc.close()
    s = 72.0 / dpi
    words: list[Word] = []
    for ln in tsv.splitlines()[1:]:
        c = ln.split("\t")
        if len(c) < 12 or c[0] != "5" or not c[11].strip():
            continue
        l, t, w, h = (int(c[6]), int(c[7]), int(c[8]), int(c[9]))
        words.append(Word(c[11], l * s, t * s, (l + w) * s, (t + h) * s, (c[2], c[3], c[4])))
    return txt, words


def find_spans(words: list[Word], rx: re.Pattern) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Regex over each OCR line (words joined by one space) → matched text + union box."""
    lines: dict[tuple, list[Word]] = {}
    for w in words:
        lines.setdefault(w.line, []).append(w)
    out = []
    for ws in lines.values():
        ws.sort(key=lambda w: w.x0)
        s, spans = "", []
        for w in ws:
            if s:
                s += " "
            spans.append((len(s), len(s) + len(w.text), w))
            s += w.text
        for m in rx.finditer(s):
            hit = [w for a, b, w in spans if a < m.end() and b > m.start()]
            if hit:
                out.append((m.group(0), (min(w.x0 for w in hit), min(w.y0 for w in hit),
                                         max(w.x1 for w in hit), max(w.y1 for w in hit))))
    return out


def reread_clip(path: str | Path, rect: tuple[float, float, float, float], *, page: int = 0,
                dpis: tuple[int, ...] = (200, 300, 400), whitelist: str = "0123456789.,KGS",
                pad: tuple[float, float, float, float] = (1.0, 0.5, 0.6, 0.5),
                clean_per_300dpi: int = 0, psm: str = "7") -> list[tuple[int, str]]:
    """Re-OCR one located value as a single line at several zooms.

    ``pad`` = (left, top, right, bottom) in multiples of the box height.
    ``clean_per_300dpi`` > 0 removes hatch lines first (k scaled with dpi).
    Returns ``[(dpi, text), ...]``.
    """
    import pymupdf

    tess = _ocr.find_tesseract()
    p = Path(path)
    if tess is None or not p.is_file():
        return []
    x0, y0, x1, y1 = rect
    hgt = max(1.0, y1 - y0)
    doc = pymupdf.open(p)
    out: list[tuple[int, str]] = []
    # keep glyphs ≥ ~14 px tall at the first zoom (small photos / tiny print)
    f = max(1.0, 14.0 / (hgt * dpis[0] / 72.0))
    dpis = tuple(int(d * f) for d in dpis)
    try:
        pr = doc[page].rect
        clip = pymupdf.Rect(max(pr.x0, x0 - pad[0] * hgt), max(pr.y0, y0 - pad[1] * hgt),
                            min(pr.x1, x1 + pad[2] * hgt), min(pr.y1, y1 + pad[3] * hgt))
        with tempfile.TemporaryDirectory(prefix="rrc_") as td:
            for dpi in dpis:
                k = round(clean_per_300dpi * dpi / 300) if clean_per_300dpi else 0
                pix = _render(doc, page, dpi, clip=clip, clean_k=k)
                img = Path(td) / f"c{dpi}.png"
                pix.save(str(img))
                t = _run([str(tess), str(img), "stdout", "--psm", str(psm), "-c",
                          f"tessedit_char_whitelist={whitelist}"], tess).strip()
                out.append((dpi, t))
    finally:
        doc.close()
    return out


def line_height(words: list[Word], default: float = 8.0) -> float:
    """Median word-box height in points (typewriter body text), clamped 6–12."""
    hs = sorted(w.y1 - w.y0 for w in words if w.text.strip() and len(w.text) > 1)
    if not hs:
        return default
    return max(6.0, min(12.0, hs[len(hs) // 2]))


def line_run(words: list[Word], rect: tuple[float, float, float, float], *,
             max_gap: float, max_width: float) -> tuple[float, float, float, float]:
    """Extend ``rect`` rightwards over the words of the same OCR line that follow
    it with gaps ≤ ``max_gap`` (a printed value after its label), capped at
    ``max_width`` from ``rect``'s left edge."""
    x0, y0, x1, y1 = rect
    yc = (y0 + y1) / 2
    same = sorted((w for w in words if w.y0 <= yc <= w.y1 and w.x0 >= x1 - 0.5), key=lambda w: w.x0)
    for w in same:
        if w.x0 - x1 > max_gap or w.x1 - x0 > max_width:
            break
        x1 = max(x1, w.x1)
    return (x0, y0, x1, y1)
