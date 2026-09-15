"""Hard checks for BL / arrival-notice extracts."""

from __future__ import annotations

from typing import Any, Optional


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def hard_check_bl(extract: dict[str, Any]) -> dict[str, Any]:
    """Return ``{verdict, issues, details}`` for a BL extract dict.

    Pass requires a BL/HBL number and at least one of packages / GW / ETA
    (enough to reconcile with INV later). Soft-missing vessel/ports OK.
    """
    header = extract.get("header") or {}
    meta = extract.get("meta") or {}
    issues: list[str] = []
    details: dict[str, Any] = {}

    if meta.get("needs_ocr") or meta.get("needs_gold"):
        return {
            "verdict": "needs_gold",
            "issues": ["needs_ocr or needs_gold flagged"],
            "details": {},
        }

    bl = header.get("bl_no") or header.get("hbl_no")
    if not bl:
        issues.append("missing bl_no/hbl_no")

    pkg = _f(header.get("packages"))
    gw = _f(header.get("gross_weight_kg"))
    eta = header.get("eta")
    details["anchors"] = {
        "bl_no": bl,
        "packages": pkg,
        "gross_weight_kg": gw,
        "eta": eta,
    }
    if pkg is None and gw is None and not eta:
        issues.append("missing packages, gross_weight_kg, and eta (need ≥1)")

    if pkg is not None and pkg <= 0:
        issues.append(f"packages non-positive: {pkg}")
    if gw is not None and gw <= 0:
        issues.append(f"gross_weight_kg non-positive: {gw}")

    if issues:
        return {"verdict": "conflict", "issues": issues, "details": details}
    return {"verdict": "pass", "issues": [], "details": details}
