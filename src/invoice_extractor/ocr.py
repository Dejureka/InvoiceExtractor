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
    """Return the directory that contains ``*.traineddata`` files.

    Honors ``TESSDATA_PREFIX`` when it already points at that directory, or at
    its parent (legacy Linux layout where PREFIX/tessdata/ holds the files).
    Otherwise looks for ``tessdata/`` next to the portable binary.
    """
    env = (os.environ.get("TESSDATA_PREFIX") or "").strip()
    if env:
        p = Path(env)
        if p.is_dir():
            if any(p.glob("*.traineddata")):
                return p
            nested = p / "tessdata"
            if nested.is_dir() and any(nested.glob("*.traineddata")):
                return nested
    # Common portable layout: tesseract/tessdata next to binary
    for parent in (tess_bin.parent, tess_bin.parent.parent):
        td = parent / "tessdata"
        if td.is_dir():
            return td
    return None


def tesseract_available() -> bool:
    return find_tesseract() is not None


def _run_tesseract(img: Path, out_base: Path, *, lang: str, tess_bin: Path) -> str:
    env = _tesseract_env(tess_bin)

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


# ---------------------------------------------------------------------------
# Standalone: scan PDF → searchable / copyable PDF (text layer)
# ---------------------------------------------------------------------------

OCR_OUT_DIRNAME = "ocr_out"
OCR_OUTPUT_SUFFIX = ".ocr.pdf"  # foo.pdf → foo.ocr.pdf


def app_root() -> Path:
    """Portable app root (same as export.tool_root when available)."""
    try:
        from invoice_extractor.export import tool_root

        return tool_root()
    except Exception:
        if getattr(sys, "frozen", False):
            try:
                return Path(sys.executable).resolve().parent
            except Exception:
                pass
        return Path.cwd()


def default_ocr_out_dir(root: Path | None = None) -> Path:
    """Default output folder: ``ocr_out/`` next to the portable app root.

    Created on demand by callers / ``pdf_to_searchable_pdf``. Empty until used;
    outputs are user-generated.
    """
    base = root if root is not None else app_root()
    return Path(base) / OCR_OUT_DIRNAME


def ocr_output_name(src: Path) -> str:
    """Naming scheme: keep stem + ``.ocr.pdf`` (e.g. ``foo.pdf`` → ``foo.ocr.pdf``)."""
    return f"{src.stem}{OCR_OUTPUT_SUFFIX}"


def resolve_ocr_lang(tess_bin: Path | None = None, *, prefer: str = DEFAULT_LANG) -> str:
    """Build tesseract ``-l`` value: prefer eng; append chi_tra / chi_sim if present.

    Returns e.g. ``eng``, ``eng+chi_tra``, or ``eng+chi_tra+chi_sim``.
    """
    langs = [prefer or DEFAULT_LANG]
    td = _tessdata_dir(tess_bin) if tess_bin else None
    if td is None and tess_bin is None:
        tess_bin = find_tesseract()
        td = _tessdata_dir(tess_bin) if tess_bin else None
    elif tess_bin is not None and td is None:
        td = _tessdata_dir(tess_bin)

    # Also check system tessdata via tesseract --list-langs when no local dir
    available: set[str] = set()
    if td is not None and td.is_dir():
        for f in td.glob("*.traineddata"):
            available.add(f.stem)
    elif tess_bin is not None:
        try:
            env = os.environ.copy()
            proc = subprocess.run(
                [str(tess_bin), "--list-langs"],
                capture_output=True,
                text=True,
                env=env,
                timeout=30,
                check=False,
            )
            for line in (proc.stdout or "").splitlines():
                name = line.strip()
                if name and name != "List of available languages" and not name.startswith("---"):
                    available.add(name)
        except Exception:
            pass

    for extra in ("chi_tra", "chi_sim"):
        if extra in available and extra not in langs:
            langs.append(extra)
    return "+".join(langs)


def _tesseract_env(tess_bin: Path) -> dict[str, str]:
    """Env for subprocess: ``TESSDATA_PREFIX`` = dir with ``*.traineddata``.

    Modern Windows Tesseract (UB Mannheim / Chocolatey) looks for
    ``$TESSDATA_PREFIX/<lang>.traineddata`` and its error text asks for the
    tessdata directory — not the parent. Setting the parent made portable
    OCR fail with ``.../tesseract/eng.traineddata`` missing.
    """
    env = os.environ.copy()
    td = _tessdata_dir(tess_bin)
    if td is not None:
        env["TESSDATA_PREFIX"] = str(td)
    return env


def _run_tesseract_pdf(img: Path, out_base: Path, *, lang: str, tess_bin: Path) -> Path:
    """Run tesseract with PDF output. Returns the produced ``.pdf`` path."""
    env = _tesseract_env(tess_bin)
    cmd = [str(tess_bin), str(img), str(out_base), "-l", lang, "--psm", "6", "pdf"]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env,
        timeout=180,
        check=False,
    )
    out_pdf = out_base.with_suffix(".pdf")
    if proc.returncode != 0 and not out_pdf.is_file():
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"tesseract pdf failed: {err}")
    if not out_pdf.is_file():
        raise RuntimeError(f"tesseract pdf produced no file: {out_pdf}")
    return out_pdf


def _merge_pdfs_pymupdf(page_pdfs: list[Path], dest: Path) -> Path:
    import pymupdf

    out = pymupdf.open()
    try:
        for p in page_pdfs:
            src = pymupdf.open(p)
            try:
                out.insert_pdf(src)
            finally:
                src.close()
        dest.parent.mkdir(parents=True, exist_ok=True)
        out.save(str(dest))
    finally:
        out.close()
    return dest


def pdf_to_searchable_pdf(
    src: str | Path,
    dest_dir: str | Path | None = None,
    *,
    lang: str | None = None,
    dpi: int = DEFAULT_DPI,
) -> Path:
    """Render a scan PDF, OCR each page to PDF, merge → searchable PDF.

    - Default ``dest_dir``: ``ocr_out/`` under app root (created if missing).
    - Output name: ``{stem}.ocr.pdf`` (see ``ocr_output_name``).
    - Does **not** run invoice extract.

    Returns the written Path.
    """
    path = Path(src)
    if not path.is_file():
        raise FileNotFoundError(f"PDF not found: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Not a PDF: {path}")

    tess = find_tesseract()
    if tess is None:
        raise RuntimeError(
            "tesseract not found (install Tesseract OCR, set TESSERACT_CMD, "
            "or place portable tesseract/ next to the app)"
        )

    out_dir = Path(dest_dir) if dest_dir is not None else default_ocr_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / ocr_output_name(path)

    use_lang = lang if lang else resolve_ocr_lang(tess)

    with tempfile.TemporaryDirectory(prefix="inv_ocr_pdf_") as td:
        tdir = Path(td)
        pages_dir = tdir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        pages = render_pdf_pages(path, pages_dir, dpi=dpi)
        if not pages:
            raise RuntimeError(f"no pages rendered from {path}")

        page_pdfs: list[Path] = []
        for i, img in enumerate(pages):
            out_base = tdir / f"page_{i:04d}"
            page_pdfs.append(
                _run_tesseract_pdf(img, out_base, lang=use_lang, tess_bin=tess)
            )

        _merge_pdfs_pymupdf(page_pdfs, dest)

    return dest


def pdfs_to_searchable_pdfs(
    sources: list[str | Path],
    dest_dir: str | Path | None = None,
    *,
    lang: str | None = None,
    dpi: int = DEFAULT_DPI,
) -> tuple[list[Path], list[tuple[Path, str]]]:
    """Batch helper. Returns ``(written_paths, failures)`` where failures are
    ``(src_path, error_message)``.
    """
    out_dir = Path(dest_dir) if dest_dir is not None else default_ocr_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    failures: list[tuple[Path, str]] = []
    for raw in sources:
        src = Path(raw)
        try:
            written.append(
                pdf_to_searchable_pdf(src, out_dir, lang=lang, dpi=dpi)
            )
        except Exception as exc:  # noqa: BLE001
            failures.append((src, str(exc)))
    return written, failures
