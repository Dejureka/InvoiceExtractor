"""Offline OCR fallback (Tesseract) when the PDF text layer is empty.

Prefers a system / PATH ``tesseract`` binary, then portable layouts next to the
app (``tesseract/tesseract.exe``, ``tesseract/bin/tesseract.exe``). Renders
pages with PyMuPDF (or poppler ``pdftoppm``) and feeds PNG rasters to Tesseract.
OCR text is intended for the *same* rules_engine classifiers — no OCR-only
format_id.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

OCR_BACKEND = "ocr/tesseract"
DEFAULT_DPI = 200
DEFAULT_LANG = "eng"


def is_ocr_backend(backend: str | None) -> bool:
    b = (backend or "").lower()
    return b.startswith("ocr/") or "tesseract" in b


def find_tesseract() -> Path | None:
    """Locate ``tesseract`` executable (env, PATH, or portable bundle)."""
    env = (os.environ.get("TESSERACT_CMD") or "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p

    which = shutil.which("tesseract") or shutil.which("tesseract.exe")
    if which:
        return Path(which)

    candidates: list[Path] = []
    roots: list[Path] = [Path.cwd()]
    if getattr(sys, "frozen", False):
        try:
            roots.insert(0, Path(sys.executable).resolve().parent)
        except Exception:
            pass
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            roots.insert(0, Path(meipass))
    here = Path(__file__).resolve()
    # src/invoice_extractor → project root
    if len(here.parents) >= 3:
        roots.append(here.parents[2])

    for root in roots:
        for rel in (
            Path("tesseract") / "tesseract.exe",
            Path("tesseract") / "bin" / "tesseract.exe",
            Path("tesseract") / "tesseract",
            Path("tesseract") / "bin" / "tesseract",
        ):
            candidates.append(root / rel)

    for c in candidates:
        if c.is_file():
            return c
    return None


def _tessdata_dir(tess_bin: Path) -> Path | None:
    env = (os.environ.get("TESSDATA_PREFIX") or "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            return p
    # Common portable layout: tesseract/tessdata next to binary
    for parent in (tess_bin.parent, tess_bin.parent.parent):
        td = parent / "tessdata"
        if td.is_dir():
            return td
    return None


def tesseract_available() -> bool:
    return find_tesseract() is not None


def _run_tesseract(img: Path, out_base: Path, *, lang: str, tess_bin: Path) -> str:
    env = os.environ.copy()
    td = _tessdata_dir(tess_bin)
    if td is not None:
        # Tesseract expects TESSDATA_PREFIX to be the *parent* of tessdata/,
        # or the tessdata dir itself depending on version; set both safely.
        env["TESSDATA_PREFIX"] = str(td if td.name != "tessdata" else td.parent)
        # Some Windows builds want the tessdata folder path:
        env.setdefault("TESSDATA_DIR", str(td))

    cmd = [str(tess_bin), str(img), str(out_base), "-l", lang, "--psm", "6"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
        check=False,
    )
    out_txt = out_base.with_suffix(".txt")
    if proc.returncode != 0 and not out_txt.is_file():
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"tesseract failed: {err}")
    return out_txt.read_text(encoding="utf-8", errors="replace") if out_txt.is_file() else ""


def _render_pages_pymupdf(pdf_path: Path, out_dir: Path, dpi: int) -> list[Path]:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    paths: list[Path] = []
    zoom = dpi / 72.0
    mat = pymupdf.Matrix(zoom, zoom)
    try:
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=mat, alpha=False)
            dest = out_dir / f"page_{i:04d}.png"
            pix.save(str(dest))
            paths.append(dest)
    finally:
        doc.close()
    return paths


def _render_pages_pdftoppm(pdf_path: Path, out_dir: Path, dpi: int) -> list[Path]:
    pdftoppm = shutil.which("pdftoppm") or shutil.which("pdftoppm.exe")
    if not pdftoppm:
        # portable poppler next to app
        for root in (
            Path.cwd(),
            Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None,
        ):
            if root is None:
                continue
            cand = root / "poppler" / "bin" / "pdftoppm.exe"
            if cand.is_file():
                pdftoppm = str(cand)
                break
    if not pdftoppm:
        raise RuntimeError("pdftoppm not found (and pymupdf unavailable)")

    prefix = out_dir / "page"
    proc = subprocess.run(
        [pdftoppm, "-png", "-r", str(dpi), str(pdf_path), str(prefix)],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(f"pdftoppm failed: {err}")
    pages = sorted(out_dir.glob("page*.png"))
    if not pages:
        raise RuntimeError("pdftoppm produced no PNG pages")
    return pages


def render_pdf_pages(pdf_path: Path, out_dir: Path, dpi: int = DEFAULT_DPI) -> list[Path]:
    try:
        return _render_pages_pymupdf(pdf_path, out_dir, dpi)
    except Exception:
        return _render_pages_pdftoppm(pdf_path, out_dir, dpi)


def ocr_pdf(
    pdf_path: str | Path,
    *,
    lang: str = DEFAULT_LANG,
    dpi: int = DEFAULT_DPI,
) -> tuple[str, str]:
    """OCR a PDF. Returns ``(text, backend)`` where backend is ``ocr/tesseract``.

    Raises ``RuntimeError`` if tesseract is missing or OCR produces no usable text
    path (empty text still returns successfully with empty string).
    """
    path = Path(pdf_path)
    tess = find_tesseract()
    if tess is None:
        raise RuntimeError(
            "tesseract not found (install Tesseract OCR, set TESSERACT_CMD, "
            "or place portable tesseract/ next to the app)"
        )

    with tempfile.TemporaryDirectory(prefix="inv_ocr_") as td:
        tdir = Path(td)
        pages_dir = tdir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        pages = render_pdf_pages(path, pages_dir, dpi=dpi)
        chunks: list[str] = []
        for i, img in enumerate(pages):
            out_base = tdir / f"ocr_{i:04d}"
            chunk = _run_tesseract(img, out_base, lang=lang, tess_bin=tess)
            chunks.append(chunk.rstrip() + "\n")
        text = "\f".join(chunks)
    return text, OCR_BACKEND


def try_ocr_pdf(
    pdf_path: str | Path,
    *,
    lang: str = DEFAULT_LANG,
    dpi: int = DEFAULT_DPI,
) -> tuple[str | None, str | None, str | None]:
    """Best-effort OCR. Returns ``(text, backend, error)``.

    On success ``error`` is None. On failure ``text``/``backend`` are None and
    ``error`` explains why (missing binary, render failure, …).
    """
    try:
        text, backend = ocr_pdf(pdf_path, lang=lang, dpi=dpi)
        return text, backend, None
    except Exception as exc:  # noqa: BLE001 — surface to meta.notes
        return None, None, str(exc)
