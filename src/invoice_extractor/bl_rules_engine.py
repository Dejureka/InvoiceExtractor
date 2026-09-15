"""Classify and extract BL / arrival-notice / HBL PDFs."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from invoice_extractor.formats.bl import (
    ceva_pyramid_arrival_v1,
    dhl_lcl_arrival_v1,
    hippopo_hbl_v1,
    milestone_arrival_v1,
)
from invoice_extractor.schema_bl import BLExtractResult, BLHeader, BLMeta

BLExtractor = Callable[[str, str, str, bool], BLExtractResult]

BUILTIN_BL: list[tuple[str, Callable[[str, str], float], BLExtractor]] = [
    ("ceva_pyramid_arrival_v1", ceva_pyramid_arrival_v1.match_score, ceva_pyramid_arrival_v1.extract),
    ("dhl_lcl_arrival_v1", dhl_lcl_arrival_v1.match_score, dhl_lcl_arrival_v1.extract),
    ("hippopo_hbl_v1", hippopo_hbl_v1.match_score, hippopo_hbl_v1.extract),
    ("milestone_arrival_v1", milestone_arrival_v1.match_score, milestone_arrival_v1.extract),
]


def classify_bl(text: str, filename: str = "") -> tuple[Optional[str], float]:
    best_id: Optional[str] = None
    best = 0.0
    for fid, scorer, _ in BUILTIN_BL:
        s = scorer(text, filename)
        if s > best:
            best = s
            best_id = fid
    if best < 0.3:
        return None, best
    return best_id, best


def apply_bl_format(
    format_id: str,
    path: str,
    text: str,
    backend: str,
    needs_ocr: bool,
) -> BLExtractResult:
    for fid, _, extractor in BUILTIN_BL:
        if fid == format_id:
            return extractor(path, text, backend, needs_ocr)
    raise KeyError(f"unknown BL format_id: {format_id}")


def looks_like_bl_filename(name: str) -> bool:
    """Cheap filename gate used to skip BL PDFs in invoice pairing batches."""
    import re

    n = name
    nu = name.upper()
    if "到貨" in n or "提單" in n:
        return True
    if "HBL" in nu or "ARRIVAL" in nu:
        return True
    if re.search(r"\bBL[#_\- ]|B/L", nu):
        return True
    if re.search(r"\bHB\d{8}\b", nu):
        return True
    return False


def extract_bl(
    pdf_path: str | Path,
    *,
    text: str | None = None,
    backend: str | None = None,
    needs_ocr: bool | None = None,
    format_id: str | None = None,
) -> BLExtractResult:
    """High-level: text layer → classify BL family → rules extract."""
    from invoice_extractor.text_layer import extract_layout_text

    path = Path(pdf_path)
    if text is None:
        text, backend2, needs_ocr2 = extract_layout_text(path)
        backend = backend or backend2
        needs_ocr = needs_ocr2 if needs_ocr is None else needs_ocr
    else:
        backend = backend or "provided"
        needs_ocr = bool(needs_ocr) if needs_ocr is not None else not text.strip()

    if needs_ocr:
        return BLExtractResult(
            header=BLHeader(),
            meta=BLMeta(
                source_file=str(path),
                text_backend=backend or "",
                confidence="needs_gold",
                needs_ocr=True,
                needs_gold=True,
                notes="empty text layer",
                doc_kind="bl",
            ),
        )

    fid = format_id
    score = 1.0
    if not fid:
        fid, score = classify_bl(text, path.name)
    if not fid:
        return BLExtractResult(
            header=BLHeader(),
            meta=BLMeta(
                source_file=str(path),
                text_backend=backend or "",
                confidence="needs_gold",
                needs_gold=True,
                notes=f"no BL format matched (best_score={score})",
                doc_kind="bl",
            ),
        )

    result = apply_bl_format(fid, str(path), text, backend or "", bool(needs_ocr))
    if score < 0.5 and result.meta.confidence == "rules":
        result.meta.notes = (result.meta.notes or "") + f" low_match={score:.2f}"
    return result
