"""Wrap pdf_layout_text; Excel workbook text; flag empty text as needs_ocr; OCR fallback."""

from __future__ import annotations

from pathlib import Path

from invoice_extractor.excel_text import (
    ExcelUnsupportedError,
    is_excel_path,
    workbook_to_text,
)
from invoice_extractor.ocr import OCR_BACKEND, is_ocr_backend, try_ocr_pdf

# Backends that preserve BITZER/PT column layout best.
PREFERRED_BACKEND_PREFIX = "pdftotext"


def extract_layout_text(pdf_path: str | Path) -> tuple[str, str, bool]:
    """Return ``(text, backend, needs_ocr)``.

    ``needs_ocr`` is True when the text layer is empty / whitespace-only.
    Does **not** run OCR — call :func:`extract_text` for the OCR fallback.
    Excel inputs are converted via openpyxl (never OCR).
    """
    path = Path(pdf_path)
    if is_excel_path(path):
        try:
            text, backend = workbook_to_text(path)
        except ExcelUnsupportedError as exc:
            return "", f"excel/error:{exc}", True
        return text or "", backend, not (text or "").strip()

    from pdf_layout_text import pdf_to_layout_text

    text, backend = pdf_to_layout_text(path)
    needs_ocr = not (text or "").strip()
    if needs_ocr:
        sidecar = path.with_suffix(path.suffix + ".ocr.txt")
        if not sidecar.exists():
            sidecar = path.with_name(path.stem + ".ocr.txt")
        if sidecar.exists():
            text = sidecar.read_text(encoding="utf-8", errors="replace")
            backend = (backend or "") + "+ocr_sidecar"
            needs_ocr = not (text or "").strip()
    return text or "", backend, needs_ocr


def extract_text(
    pdf_path: str | Path,
    *,
    allow_ocr: bool = True,
) -> tuple[str, str, bool]:
    """Layout text, then optional Tesseract OCR when the layer is empty.

    Returns ``(text, backend, needs_ocr)``.

    - Excel (``.xlsx``/``.xlsm``): cell text via openpyxl; never OCR.
    - If the native text layer has content: ``needs_ocr=False``, normal backend.
    - If empty and OCR succeeds with non-empty text: ``backend`` is
      ``ocr/tesseract`` (or equivalent), ``needs_ocr=False`` so the same
      rules_engine path can classify/extract.
    - If empty and OCR unavailable / empty: ``needs_ocr=True``, original
      (empty) backend preserved when possible.
    """
    path = Path(pdf_path)
    # Excel: never attempt OCR (binary workbook / not a scan PDF).
    if is_excel_path(path):
        return extract_layout_text(path)

    text, backend, needs_ocr = extract_layout_text(path)
    if not needs_ocr or not allow_ocr:
        return text, backend, needs_ocr

    ocr_text, ocr_backend, err = try_ocr_pdf(path)
    if ocr_text is not None and ocr_text.strip():
        return ocr_text, ocr_backend or OCR_BACKEND, False

    # Keep empty text; annotate backend so callers can surface the OCR error.
    note_backend = backend or ""
    if err:
        note_backend = f"{note_backend}+ocr_failed" if note_backend else "ocr_failed"
    return text, note_backend, True


def backend_is_preferred(backend: str | None) -> bool:
    return bool(backend) and str(backend).startswith(PREFERRED_BACKEND_PREFIX)


def backend_warning(backend: str | None) -> str | None:
    """Human-readable note when not using poppler pdftotext (or when OCR used)."""
    if backend and str(backend).startswith("excel/"):
        if "error:" in str(backend):
            return str(backend).split("error:", 1)[-1].strip() or "Excel read failed"
        return None
    if is_ocr_backend(backend):
        return (
            f"OCR used ({backend}): PDF text layer was empty. "
            "Column layout may be imperfect vs pdftotext; rules still apply."
        )
    if backend and "ocr_failed" in str(backend):
        return (
            f"Text layer empty and OCR failed/unavailable (backend={backend}). "
            "Install Tesseract or use a portable-ocr-test zip that bundles it."
        )
    if backend_is_preferred(backend):
        return None
    return (
        f"Text backend is '{backend or 'unknown'}' (poppler pdftotext not found). "
        "Layout may be poorer; BITZER/PT extracts are best with bundled or PATH pdftotext. "
        "Portable builds should include poppler/bin/pdftotext.exe next to the app."
    )
