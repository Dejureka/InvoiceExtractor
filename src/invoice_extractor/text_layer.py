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


def _garbage_char_ratio(s: str) -> float:
    """Fraction of chars that look like binary / private-use garbage (not normal text)."""
    if not s:
        return 0.0
    weird = 0
    n = 0
    for c in s:
        if c in "\n\r\t ":
            continue
        n += 1
        o = ord(c)
        if o < 32 or (0x7F <= o < 0xA0) or (0xE000 <= o <= 0xF8FF):
            weird += 1
    return (weird / n) if n else 0.0


def text_layer_looks_unreliable(text: str) -> bool:
    """True when the PDF text layer looks stale/corrupt vs a visible scan page.

    Heuristics (generic — not filename-specific):
    - High overall ratio of control / private-use characters
    - Any page after the first that is mostly binary garbage (common when an
      image page still carries leftover text objects from another document)
    """
    if not (text or "").strip():
        return True
    if _garbage_char_ratio(text) > 0.08 and len(text) > 200:
        return True
    pages = text.split("\f")
    for page in pages[1:]:
        if len(page.strip()) < 80:
            continue
        if _garbage_char_ratio(page) > 0.12:
            return True
    return False


def ocr_text_looks_more_reliable(layer: str, ocr: str) -> bool:
    """Prefer OCR when it recovers packing/invoice anchors the layer lacks,
    or when the layer is garbage-heavy while OCR is mostly printable."""
    if not (ocr or "").strip():
        return False
    if text_layer_looks_unreliable(layer) and _garbage_char_ratio(ocr) < 0.05:
        return True
    # Layer has an Invoice No. but packing body contradicts OCR's clear TOTAL PALLETS/GW
    import re
    ocr_has_pallet_total = bool(
        re.search(r"TOTAL\s*:?\s*\d+\s*PALLETS?|\(\s*TOTAL\s*:?\s*\d+\s*PALLETS?", ocr, re.I)
    )
    layer_has_pallet_total = bool(re.search(r"\d+\s*PALLETS?", layer or "", re.I))
    if ocr_has_pallet_total and not layer_has_pallet_total:
        # and OCR shares an invoice token with the layer header (same doc) or layer is thin
        invs_ocr = set(re.findall(r"\b(USDI\d+|VKT\d+|9027\d{6}|OK\d{8})\b", ocr, re.I))
        invs_layer = set(re.findall(r"\b(USDI\d+|VKT\d+|9027\d{6}|OK\d{8})\b", layer or "", re.I))
        if invs_ocr and (invs_ocr & invs_layer or not invs_layer):
            return True
    return False


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
    if not allow_ocr:
        return text, backend, needs_ocr

    # Empty layer → OCR. Non-empty but unreliable/stale (garbage pages / high
    # binary ratio) → OCR and prefer it. Clean text layers are left alone
    # (no blanket OCR on every PDF).
    stale = (not needs_ocr) and text_layer_looks_unreliable(text)
    if not needs_ocr and not stale:
        return text, backend, needs_ocr

    ocr_text, ocr_backend, err = try_ocr_pdf(path)
    if ocr_text is not None and ocr_text.strip():
        tag = ocr_backend or OCR_BACKEND
        if stale:
            # Only swap when OCR is clearly better; otherwise keep layer
            if ocr_text_looks_more_reliable(text, ocr_text) or needs_ocr:
                tag = f"{tag}+prefer_over_stale_layer" if stale else tag
                return ocr_text, tag, False
            return text, backend, False
        return ocr_text, tag, False

    # Keep empty/stale text; annotate backend so callers can surface the OCR error.
    note_backend = backend or ""
    if err:
        note_backend = f"{note_backend}+ocr_failed" if note_backend else "ocr_failed"
    return text, note_backend, True if needs_ocr else False


def backend_is_preferred(backend: str | None) -> bool:
    return bool(backend) and str(backend).startswith(PREFERRED_BACKEND_PREFIX)


def backend_warning(backend: str | None) -> str | None:
    """Human-readable note when not using poppler pdftotext (or when OCR used)."""
    if backend and str(backend).startswith("excel/"):
        if "error:" in str(backend):
            return str(backend).split("error:", 1)[-1].strip() or "Excel read failed"
        return None
    if is_ocr_backend(backend) or (backend and "prefer_over_stale_layer" in str(backend)):
        if backend and "prefer_over_stale_layer" in str(backend):
            return (
                f"OCR preferred ({backend}): PDF text layer looked stale/corrupt "
                "or contradicted visible packing anchors; rules use OCR text."
            )
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
