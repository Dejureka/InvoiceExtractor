"""Format-mapping status labels for GUI / RunSOP summary lines."""

from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

AUDITED_REL = Path("data") / "audited_formats.json"

# Public labels (shown in GUI / RunSOP)
LABEL_AUDIT_OK = "audit ok"
LABEL_KNOWN_UNAUDITED = "已知未審"
LABEL_NEW_NEEDS_RULES = "全新／需規則"
LABEL_HARD_FAIL = "hard fail"


def audited_formats_path() -> Path | None:
    """Locate shipped ``audited_formats.json`` (dev / installed / frozen)."""
    candidates: list[Path] = []
    here = Path(__file__).resolve()
    candidates.append(here.parents[2] / AUDITED_REL)
    candidates.append(here.parents[1] / AUDITED_REL)
    candidates.append(Path.cwd() / AUDITED_REL)
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.insert(0, Path(meipass) / AUDITED_REL)
        try:
            candidates.insert(0, Path(sys.executable).resolve().parent / AUDITED_REL)
        except Exception:
            pass
    for p in candidates:
        if p.is_file():
            return p
    return None


@lru_cache(maxsize=1)
def load_audited_format_ids() -> frozenset[str]:
    """Return set of format_ids marked audited in the registry (empty if missing)."""
    path = audited_formats_path()
    if path is None:
        return frozenset()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return frozenset()
    formats = data.get("formats") or {}
    out: set[str] = set()
    for fid, info in formats.items():
        if isinstance(info, dict):
            if info.get("audited", True):
                out.add(str(fid))
        elif info:
            out.add(str(fid))
    return frozenset(out)


def clear_audited_cache() -> None:
    """Test helper: drop cached registry."""
    load_audited_format_ids.cache_clear()


def checker_display(checker_verdict: str | None) -> str:
    """Short checker column for summary lines (``hard pass`` / ``hard fail`` / …)."""
    v = (checker_verdict or "").strip().lower()
    if v == "pass":
        return "hard pass"
    if v == "conflict":
        return "hard fail"
    if v == "needs_gold":
        return "needs_gold"
    return v or "—"


def mapping_status(
    meta: dict[str, Any] | None,
    checker_verdict: str | None = None,
    *,
    audited_ids: frozenset[str] | None = None,
) -> str:
    """Classify format-mapping status for one extract.

    Priority:
    1. ``hard fail`` — checker conflict
    2. ``全新／需規則`` — no format_id / needs_gold / empty text / needs_ocr
    3. ``audit ok`` — format_id in AuditSOP registry
    4. ``已知未審`` — matched format_id but not in registry
    """
    meta = meta or {}
    verdict = (checker_verdict or meta.get("checker_verdict") or "").strip().lower()
    if verdict == "conflict":
        return LABEL_HARD_FAIL

    fid = meta.get("format_id")
    fid_s = str(fid).strip() if fid else ""
    needs_rules = (
        not fid_s
        or bool(meta.get("needs_gold"))
        or bool(meta.get("needs_ocr"))
        or verdict == "needs_gold"
        or (meta.get("confidence") == "needs_gold")
    )
    if needs_rules:
        return LABEL_NEW_NEEDS_RULES

    ids = audited_ids if audited_ids is not None else load_audited_format_ids()
    if fid_s in ids:
        return LABEL_AUDIT_OK
    return LABEL_KNOWN_UNAUDITED


def format_status_line(
    *,
    invoice_no: Any = None,
    format_id: Any = None,
    mapping: str,
    checker_verdict: str | None = None,
) -> str:
    """``50666223 | pt_gloria_v1 | audit ok | hard pass``."""
    inv = invoice_no if invoice_no not in (None, "") else "—"
    fid = format_id if format_id not in (None, "") else "—"
    return f"{inv} | {fid} | {mapping} | {checker_display(checker_verdict)}"


def count_mapping_statuses(labels: list[str]) -> dict[str, int]:
    """Count occurrences of each mapping label (stable key order)."""
    order = [
        LABEL_AUDIT_OK,
        LABEL_KNOWN_UNAUDITED,
        LABEL_NEW_NEEDS_RULES,
        LABEL_HARD_FAIL,
    ]
    counts = {k: 0 for k in order}
    for lab in labels:
        if lab in counts:
            counts[lab] += 1
        else:
            counts[lab] = counts.get(lab, 0) + 1
    return counts
