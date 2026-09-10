"""Convert PDF to layout-preserving plain text.

Backend priority:
1. Bundled or PATH poppler ``pdftotext -layout`` (best layout fidelity)
2. pymupdf ``page.get_text("text")`` (if installed; bundled in portable)
3. pdfminer.six with LAParams tuned for layout-ish extraction
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _bundled_pdftotext_candidates() -> list[Path]:
    """Locate pdftotext shipped next to the app / PyInstaller bundle."""
    cands: list[Path] = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        base = Path(meipass)
        cands += [
            base / "poppler" / "Library" / "bin" / "pdftotext.exe",
            base / "poppler" / "bin" / "pdftotext.exe",
            base / "poppler" / "pdftotext.exe",
            base / "pdftotext.exe",
            base / "poppler" / "bin" / "pdftotext",
            base / "pdftotext",
        ]
    exe_dir = Path(sys.executable).resolve().parent
    cands += [
        exe_dir / "poppler" / "Library" / "bin" / "pdftotext.exe",
        exe_dir / "poppler" / "bin" / "pdftotext.exe",
        exe_dir / "poppler" / "pdftotext.exe",
        exe_dir / "pdftotext.exe",
        exe_dir / "poppler" / "bin" / "pdftotext",
        exe_dir / "pdftotext",
    ]
    here = Path(__file__).resolve()
    for root in [here.parents[2], here.parents[1], Path.cwd()]:
        cands += [
            root / "vendor" / "poppler" / "Library" / "bin" / "pdftotext.exe",
            root / "vendor" / "poppler" / "bin" / "pdftotext.exe",
            root / "vendor" / "poppler" / "bin" / "pdftotext",
            root / "poppler" / "bin" / "pdftotext.exe",
            root / "poppler" / "bin" / "pdftotext",
        ]
    return cands


def find_pdftotext() -> str | None:
    """Return path to pdftotext binary, or None."""
    env = os.environ.get("PDFTOTEXT_PATH") or os.environ.get("POPPLER_PDFTOTEXT")
    if env and Path(env).is_file():
        return env
    which = shutil.which("pdftotext")
    if which:
        return which
    for p in _bundled_pdftotext_candidates():
        if p.is_file():
            return str(p)
    return None


def _via_pdftotext(pdf_path: Path, bin_path: str | None = None) -> str:
    exe = bin_path or find_pdftotext()
    if not exe:
        raise FileNotFoundError("pdftotext not found")
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        out = Path(tmp.name)
    try:
        subprocess.run(
            [exe, "-layout", str(pdf_path), str(out)],
            check=True,
            capture_output=True,
        )
        return out.read_text(encoding="utf-8", errors="replace")
    finally:
        out.unlink(missing_ok=True)


def _via_pymupdf(pdf_path: Path) -> str:
    try:
        import pymupdf as fitz
    except ImportError:
        import fitz  # pymupdf legacy

    doc = fitz.open(str(pdf_path))
    try:
        parts = [page.get_text("text") for page in doc]
        return "\n".join(parts)
    finally:
        doc.close()


def _via_pdfminer(pdf_path: Path) -> str:
    from pdfminer.high_level import extract_text
    from pdfminer.layout import LAParams

    laparams = LAParams(
        line_margin=0.5,
        char_margin=2.0,
        word_margin=0.1,
        boxes_flow=0.5,
    )
    return extract_text(str(pdf_path), laparams=laparams) or ""


def pdf_to_layout_text(pdf_path: str | Path) -> tuple[str, str]:
    """Return ``(text, backend_name)``.

    ``backend_name`` is one of:
    ``pdftotext -layout``, ``pdftotext -layout (bundled)``,
    ``pymupdf get_text(text)``, ``pdfminer.six LAParams``.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path}")

    pdt = find_pdftotext()
    if pdt:
        text = _via_pdftotext(path, pdt)
        which = shutil.which("pdftotext")
        if which and Path(pdt).resolve() == Path(which).resolve():
            label = "pdftotext -layout"
        elif which is None:
            label = "pdftotext -layout (bundled)"
        else:
            label = "pdftotext -layout"
        return text, label

    try:
        return _via_pymupdf(path), "pymupdf get_text(text)"
    except ImportError:
        pass
    except Exception:
        pass

    try:
        return _via_pdfminer(path), "pdfminer.six LAParams"
    except Exception as e:
        raise RuntimeError(
            f"No PDF backend succeeded for {path}. "
            "Install poppler (pdftotext), pymupdf, or pdfminer.six. "
            f"Last error: {e}"
        ) from e
