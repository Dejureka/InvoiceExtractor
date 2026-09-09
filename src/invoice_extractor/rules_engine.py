"""Classify vendor format and apply extractors."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Optional

from invoice_extractor.formats import (
    bitzer_v1,
    hangji_v1,
    highly_v1,
    hitachi_gls_v1,
    nidec_v1,
    pt_gloria_v1,
)
from invoice_extractor.schema import ExtractResult, Header, Meta

Extractor = Callable[[str, str, str, bool], ExtractResult]

BUILTIN: list[tuple[str, Callable[[str, str], float], Extractor]] = [
    ("bitzer_v1", bitzer_v1.match_score, bitzer_v1.extract),
    ("pt_gloria_v1", pt_gloria_v1.match_score, pt_gloria_v1.extract),
    ("hangji_v1", hangji_v1.match_score, hangji_v1.extract),
    ("nidec_v1", nidec_v1.match_score, nidec_v1.extract),
    ("hitachi_gls_v1", hitachi_gls_v1.match_score, hitachi_gls_v1.extract),
    ("highly_v1", highly_v1.match_score, highly_v1.extract),
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


def extract_invoice(
    pdf_path: str | Path,
    *,
    text: str | None = None,
    backend: str | None = None,
    needs_ocr: bool | None = None,
    format_id: str | None = None,
) -> ExtractResult:
    """High-level: text layer → classify → rules extract."""
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
        return ExtractResult(
            header=Header(),
            items=[],
            meta=Meta(
                source_file=str(path),
                text_backend=backend or "",
                confidence="needs_gold",
                needs_ocr=True,
                needs_gold=True,
                notes="empty text layer",
            ),
        )

    fid = format_id
    score = 1.0
    if not fid:
        fid, score = classify(text, path.name)
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
            ),
        )

    result = apply_format(fid, str(path), text, backend or "", bool(needs_ocr))
    if score < 0.5 and result.meta.confidence == "rules":
        result.meta.notes = (result.meta.notes or "") + f" low_match={score:.2f}"
    return result


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
