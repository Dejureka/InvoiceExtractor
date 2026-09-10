"""Hard checks only (local, required).

When a document-labeled total is present (meta.labeled_amount / Final amount),
compare *both* header.amount and sum(items) against that labeled total so
incomplete extracts cannot pass by setting header.amount = sum(items).
"""

from __future__ import annotations

from typing import Any, Optional

AMOUNT_TOL = 0.05
QTY_TOL = 1e-6


def _f(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _labeled_total(extract: dict[str, Any]) -> tuple[Optional[float], Optional[str]]:
    """Return (amount, label) from meta / header if a document total was captured."""
    meta = extract.get("meta") or {}
    header = extract.get("header") or {}
    for key, label_key in (
        ("labeled_amount", "labeled_amount_label"),
        ("final_amount", None),
        ("invoice_total_labeled", None),
    ):
        val = _f(meta.get(key))
        if val is None:
            val = _f(header.get(key))
        if val is not None:
            label = None
            if label_key:
                label = meta.get(label_key) or header.get(label_key)
            return val, label or key
    return None, None


def hard_check(extract: dict[str, Any]) -> dict[str, Any]:
    """Return ``{verdict, issues, details}``.

    Verdict: ``pass`` | ``conflict`` | ``needs_gold``.
    """
    header = extract.get("header") or {}
    items = extract.get("items") or []
    meta = extract.get("meta") or {}
    issues: list[str] = []
    details: dict[str, Any] = {}

    if meta.get("needs_ocr") or meta.get("needs_gold"):
        return {
            "verdict": "needs_gold",
            "issues": ["needs_ocr or needs_gold flagged"],
            "details": {},
        }

    if not header.get("invoice_no"):
        issues.append("missing header.invoice_no")

    ilc = header.get("item_line_count")
    if ilc is not None and items:
        details["item_line_count"] = {"want": ilc, "got": len(items)}
        if int(ilc) != len(items):
            issues.append(f"item_line_count {ilc} != len(items) {len(items)}")

    tq = _f(header.get("total_quantity"))
    if tq is not None and items:
        sq = sum(_f(it.get("qty")) or 0.0 for it in items)
        details["total_quantity"] = {"want": tq, "got": sq}
        if abs(sq - tq) > QTY_TOL:
            issues.append(f"sum(item.qty) {sq} != total_quantity {tq}")

    sa = sum(_f(it.get("amount")) or 0.0 for it in items) if items else None
    ha = _f(header.get("amount"))

    if ha is not None and sa is not None:
        details["amount"] = {"want": ha, "got": round(sa, 4)}
        if abs(sa - ha) > AMOUNT_TOL:
            issues.append(f"sum(item.amount) {sa} != header.amount {ha}")

    labeled, label_name = _labeled_total(extract)
    if labeled is not None:
        details["labeled_amount"] = {
            "label": label_name,
            "want": labeled,
            "header_amount": ha,
            "sum_items": round(sa, 4) if sa is not None else None,
            "item_count": len(items),
        }
        if ha is None or abs(ha - labeled) > AMOUNT_TOL:
            issues.append(
                f"header.amount {ha} != labeled {label_name} {labeled}"
            )
        if sa is None or abs(sa - labeled) > AMOUNT_TOL:
            issues.append(
                f"sum(item.amount) {sa} != labeled {label_name} {labeled}"
            )

    hc = header.get("currency")
    if hc and items:
        bad = [
            i
            for i, it in enumerate(items)
            if it.get("currency") and it.get("currency") != hc
        ]
        if bad:
            issues.append(f"item currency mismatch vs header at indices {bad[:10]}")

    line_bad = []
    for i, it in enumerate(items):
        up, q, am = _f(it.get("unit_price")), _f(it.get("qty")), _f(it.get("amount"))
        if up is None or q is None or am is None:
            continue
        if abs(up * q - am) > AMOUNT_TOL:
            line_bad.append(i)
    if line_bad:
        issues.append(f"unit_price*qty != amount at indices {line_bad[:10]}")
        details["line_amount_mismatch"] = line_bad[:20]

    if not header.get("invoice_no") and not items:
        verdict = "needs_gold"
    elif issues:
        verdict = "conflict"
    else:
        verdict = "pass"

    return {"verdict": verdict, "issues": issues, "details": details}


def compare_to_gold(extract: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    """Field-level diff of header (+ optional items length)."""
    eh = extract.get("header") or {}
    gh = gold.get("header") or {}
    diffs = []
    keys = set(eh) | set(gh)
    for k in sorted(keys):
        a, b = eh.get(k), gh.get(k)
        if isinstance(a, float) or isinstance(b, float):
            af, bf = _f(a), _f(b)
            if af is None or bf is None or abs(af - bf) > AMOUNT_TOL:
                if a != b:
                    diffs.append({"field": f"header.{k}", "got": a, "gold": b})
        elif a != b:
            diffs.append({"field": f"header.{k}", "got": a, "gold": b})
    hard = hard_check(extract)
    verdict = hard["verdict"]
    if diffs and verdict == "pass":
        verdict = "conflict"
    return {"verdict": verdict, "diffs": diffs, "hard": hard}
