"""Gold-label stub: write needs_gold placeholder; optional offline JSON compare."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from invoice_extractor.checker import compare_to_gold, hard_check


def write_needs_gold_placeholder(out_path: str | Path, extract: dict[str, Any]) -> Path:
    path = Path(out_path)
    payload = {
        "status": "needs_gold",
        "message": "No LLM gold available offline. Fill header/items to use as --gold.",
        "schema_hint": {
            "header": [
                "invoice_no",
                "invoice_date",
                "total_pkg",
                "gross_weight_kg",
                "incoterm",
                "item_line_count",
                "total_quantity",
                "amount",
                "currency",
                "vendor",
            ],
            "items": [
                "invoice_no",
                "part_no",
                "description",
                "qty",
                "unit",
                "unit_price",
                "amount",
                "origin",
                "hs_code",
                "currency",
            ],
        },
        "rules_extract": extract,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_gold(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    # allow either bare extract schema or wrapped
    if "header" in data:
        return data
    if "gold" in data and isinstance(data["gold"], dict):
        return data["gold"]
    if "rules_extract" in data and "header" in (data.get("rules_extract") or {}):
        return data["rules_extract"]
    raise ValueError(f"Unrecognized gold JSON shape: {path}")


def offline_compare(extract: dict[str, Any], gold_path: str | Path) -> dict[str, Any]:
    gold = load_gold(gold_path)
    return compare_to_gold(extract, gold)


def maybe_mark_needs_gold(extract: dict[str, Any]) -> dict[str, Any]:
    meta = extract.setdefault("meta", {})
    hard = hard_check(extract)
    if hard["verdict"] == "needs_gold" or not (extract.get("header") or {}).get("invoice_no"):
        meta["needs_gold"] = True
        meta["confidence"] = "needs_gold"
    return extract
