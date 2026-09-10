"""Wrap pdf_layout_text; flag empty text as needs_ocr; surface backend quality."""

from __future__ import annotations

from pathlib import Path


# Backends that preserve BITZER/PT column layout best.
PREFERRED_BACKEND_PREFIX = "pdftotext"


def extract_layout_text(pdf_path: str | Path) -> tuple[str, str, bool]:
    """Return ``(text, backend, needs_ocr)``.

    ``needs_ocr`` is True when the text layer is empty / whitespace-only.
    """
    from pdf_layout_text import pdf_to_layout_text

    path = Path(pdf_path)
    text, backend = pdf_to_layout_text(path)
    needs_ocr = not (text or "").strip()
    return text or "", backend, needs_ocr


def backend_is_preferred(backend: str | None) -> bool:
    return bool(backend) and str(backend).startswith(PREFERRED_BACKEND_PREFIX)


def backend_warning(backend: str | None) -> str | None:
    """Human-readable warning when not using poppler pdftotext."""
    if backend_is_preferred(backend):
        return None
    return (
        f"Text backend is '{backend or 'unknown'}' (poppler pdftotext not found). "
        "Layout may be poorer; BITZER/PT extracts are best with bundled or PATH pdftotext. "
        "Portable builds should include poppler/bin/pdftotext.exe next to the app."
    )
