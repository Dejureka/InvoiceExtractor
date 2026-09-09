"""Wrap pdf_layout_text; flag empty text as needs_ocr."""

from __future__ import annotations

from pathlib import Path


def extract_layout_text(pdf_path: str | Path) -> tuple[str, str, bool]:
    """Return ``(text, backend, needs_ocr)``.

    ``needs_ocr`` is True when the text layer is empty / whitespace-only.
    """
    from pdf_layout_text import pdf_to_layout_text

    path = Path(pdf_path)
    text, backend = pdf_to_layout_text(path)
    needs_ocr = not (text or "").strip()
    return text or "", backend, needs_ocr
