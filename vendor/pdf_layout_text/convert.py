"""Convert PDF to layout-preserving plain text.

Backend priority:
1. poppler ``pdftotext -layout`` (best layout fidelity when on PATH)
2. pymupdf ``page.get_text("text")`` (if installed)
3. pdfminer.six with LAParams tuned for layout-ish extraction
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path


def _via_pdftotext(pdf_path: Path) -> str:
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        out = Path(tmp.name)
    try:
        subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), str(out)],
            check=True,
            capture_output=True,
        )
        return out.read_text(encoding="utf-8", errors="replace")
    finally:
        out.unlink(missing_ok=True)


def _via_pymupdf(pdf_path: Path) -> str:
    import fitz  # pymupdf

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
    ``pdftotext -layout``, ``pymupdf get_text(text)``, ``pdfminer.six LAParams``.
    """
    path = Path(pdf_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {path}")

    if shutil.which("pdftotext"):
        return _via_pdftotext(path), "pdftotext -layout"

    try:
        return _via_pymupdf(path), "pymupdf get_text(text)"
    except ImportError:
        pass
    except Exception:
        # fall through to pdfminer
        pass

    try:
        return _via_pdfminer(path), "pdfminer.six LAParams"
    except Exception as e:
        raise RuntimeError(
            f"No PDF backend succeeded for {path}. "
            "Install poppler (pdftotext), pymupdf, or pdfminer.six. "
            f"Last error: {e}"
        ) from e
