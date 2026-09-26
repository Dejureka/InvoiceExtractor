"""Classify vendor format and apply extractors."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Optional

from invoice_extractor.formats import (
    soe_rb_gmbh_v1,
    aichi_electric_v1,
    bhc_my_hub_v1,
    bhc_manual_inv_v1,
    marubeni_tetsugen_v1,
    shanghai_nature_v1,
    bitzer_v1,
    hangji_v1,
    highly_v1,
    hisense_qingdao_v1,
    hitachi_gls_v1,
    hitachi_asia_hitt_v1,
    ma_no_period_v1,
    ma_ak_billing_v1,
    ma_with_period_v1,
    nidec_v1,
    pt_dremel_head3_v1,
    pt_dremel_head5_v1,
    pt_gloria_v1,
    suzhou_aichi_v1,
    sumitronics_hk_v1,
    dunan_v1,
    ohizumi_dongguan_v1,
    oukai_v1,
)
from invoice_extractor.schema import ExtractResult, Header, Meta

Extractor = Callable[[str, str, str, bool], ExtractResult]

BUILTIN: list[tuple[str, Callable[[str, str], float], Extractor]] = [
    ("bitzer_v1", bitzer_v1.match_score, bitzer_v1.extract),
    ("pt_gloria_v1", pt_gloria_v1.match_score, pt_gloria_v1.extract),
    ("pt_dremel_head3_v1", pt_dremel_head3_v1.match_score, pt_dremel_head3_v1.extract),
    ("pt_dremel_head5_v1", pt_dremel_head5_v1.match_score, pt_dremel_head5_v1.extract),
    ("hangji_v1", hangji_v1.match_score, hangji_v1.extract),
    ("nidec_v1", nidec_v1.match_score, nidec_v1.extract),
    ("hitachi_gls_v1", hitachi_gls_v1.match_score, hitachi_gls_v1.extract),
    ("highly_v1", highly_v1.match_score, highly_v1.extract),
    ("ma_ak_billing_v1", ma_ak_billing_v1.match_score, ma_ak_billing_v1.extract),
    ("ma_no_period_v1", ma_no_period_v1.match_score, ma_no_period_v1.extract),
    ("ma_with_period_v1", ma_with_period_v1.match_score, ma_with_period_v1.extract),
    ("bhc_my_hub_v1", bhc_my_hub_v1.match_score, bhc_my_hub_v1.extract),
    ("hisense_qingdao_v1", hisense_qingdao_v1.match_score, hisense_qingdao_v1.extract),
    ("aichi_electric_v1", aichi_electric_v1.match_score, aichi_electric_v1.extract),
    ("shanghai_nature_v1", shanghai_nature_v1.match_score, shanghai_nature_v1.extract),
    ("marubeni_tetsugen_v1", marubeni_tetsugen_v1.match_score, marubeni_tetsugen_v1.extract),
    ("soe_rb_gmbh_v1", soe_rb_gmbh_v1.match_score, soe_rb_gmbh_v1.extract),
    ("suzhou_aichi_v1", suzhou_aichi_v1.match_score, suzhou_aichi_v1.extract),
    ("sumitronics_hk_v1", sumitronics_hk_v1.match_score, sumitronics_hk_v1.extract),
    ("dunan_v1", dunan_v1.match_score, dunan_v1.extract),
    ("ohizumi_dongguan_v1", ohizumi_dongguan_v1.match_score, ohizumi_dongguan_v1.extract),
    ("oukai_v1", oukai_v1.match_score, oukai_v1.extract),
    ("hitachi_asia_hitt_v1", hitachi_asia_hitt_v1.match_score, hitachi_asia_hitt_v1.extract),
    ("bhc_manual_inv_v1", bhc_manual_inv_v1.match_score, bhc_manual_inv_v1.extract),
]


def classify(text: str, filename: str = "") -> tuple[Optional[str], float]:
    best_id: Optional[str] = None
    best = 0.0
    for fid, scorer, _ in BUILTIN:
        s = scorer(text, filename)
        if s > best:
            best = s
            best_id = fid
    if best < 0.3:
        return None, best
    return best_id, best


def apply_format(
    format_id: str,
    path: str,
    text: str,
    backend: str,
    needs_ocr: bool,
) -> ExtractResult:
    for fid, _, extractor in BUILTIN:
        if fid == format_id:
            return extractor(path, text, backend, needs_ocr)
    raise KeyError(f"unknown format_id: {format_id}")


THIN_RETRY_MAX_PAGES = 10


def _retry_thin_layer_with_ocr(
    path: Path, text: str, backend: str | None
) -> tuple[Optional[str], float, str, str | None]:
    """No format matched on a *thin* text layer → OCR once and re-classify.

    Only runs after classification already failed, so PDFs that extract from
    their text layer today are unaffected. Returns ``(fid, score, text, backend)``;
    ``fid`` is None when OCR is unavailable or still matches nothing.
    """
    from invoice_extractor.ocr import OCR_BACKEND, is_ocr_backend, try_ocr_pdf
    from invoice_extractor.text_layer import text_layer_looks_thin

    if is_ocr_backend(backend) or not text_layer_looks_thin(text):
        return None, 0.0, text, backend
    # Invoices are short; long thin PDFs (e.g. MA Label_*.pdf, 24–138 pages)
    # never classify after OCR either, so skip the cost.
    if len(text.split("\f")) > THIN_RETRY_MAX_PAGES:
        return None, 0.0, text, backend
    ocr_text, ocr_backend, _err = try_ocr_pdf(path)
    if not ocr_text or not ocr_text.strip():
        return None, 0.0, text, backend
    fid, score = classify(ocr_text, path.name)
    if not fid:
        return None, score, text, backend
    return fid, score, ocr_text, f"{ocr_backend or OCR_BACKEND}+thin_text_layer"


def extract_invoice(
    pdf_path: str | Path,
    *,
    text: str | None = None,
    backend: str | None = None,
    needs_ocr: bool | None = None,
    format_id: str | None = None,
) -> ExtractResult:
    """High-level: text layer → classify → rules extract."""
    from invoice_extractor.excel_text import is_excel_path
    from invoice_extractor.text_layer import extract_text

    path = Path(pdf_path)
    kind = "excel" if is_excel_path(path) else "pdf"
    text_from_file = text is None
    if text is None:
        # Excel: never OCR. PDF: allow OCR fallback when text layer empty.
        text, backend2, needs_ocr2 = extract_text(path, allow_ocr=(kind == "pdf"))
        backend = backend or backend2
        needs_ocr = needs_ocr2 if needs_ocr is None else needs_ocr
    else:
        backend = backend or "provided"
        needs_ocr = bool(needs_ocr) if needs_ocr is not None else not text.strip()

    # Excel read errors (e.g. legacy .xls) surface as empty + excel/error backend.
    if kind == "excel" and (backend or "").startswith("excel/error:"):
        msg = (backend or "").split("excel/error:", 1)[-1].strip() or "Excel read failed"
        return ExtractResult(
            header=Header(),
            items=[],
            meta=Meta(
                source_file=str(path),
                text_backend=backend or "",
                confidence="needs_gold",
                needs_gold=True,
                notes=msg,
                source_kind=kind,
            ),
        )

    if needs_ocr:
        return ExtractResult(
            header=Header(),
            items=[],
            meta=Meta(
                source_file=str(path),
                text_backend=backend or "",
                confidence="needs_gold",
                needs_ocr=True,
                needs_gold=True,
                notes="empty text layer (OCR unavailable or empty)",
                source_kind=kind,
            ),
        )

    fid = format_id
    score = 1.0
    if not fid:
        fid, score = classify(text, path.name)
    if not fid and kind == "pdf" and text_from_file:
        fid2, score2, text2, backend2 = _retry_thin_layer_with_ocr(path, text, backend)
        if fid2:
            fid, score, text, backend = fid2, score2, text2, backend2
    if not fid:
        return ExtractResult(
            header=Header(),
            items=[],
            meta=Meta(
                source_file=str(path),
                text_backend=backend or "",
                confidence="needs_gold",
                needs_gold=True,
                notes=f"no format matched (best_score={score})",
                source_kind=kind,
            ),
        )

    result = apply_format(fid, str(path), text, backend or "", bool(needs_ocr))
    result.meta.source_kind = kind
    if score < 0.5 and result.meta.confidence == "rules":
        result.meta.notes = (result.meta.notes or "") + f" low_match={score:.2f}"
    return result


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
