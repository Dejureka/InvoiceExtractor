"""Rule-margin test: shrink every limit in ``windows.py`` to 80 %; outputs must not move.

A limit that only just covers the real documents (needs 48 of 55 lines…)
breaks on the next slightly longer invoice. For each constant we run the
documents of the formats that use it twice — normal and with the limit at
80 % — and compare every Result field (Summary + Lines) plus needs_gold_fields.
Corpus: cached text layers in the private store (unit/window_corpus).

Known-tight limits are ``xfail(strict=True)``: once a structural fix lands the
test starts passing, strict xfail fails, and the entry must be removed.
"""
from __future__ import annotations

import json
import math

import pytest

import samples
from conftest import require_samples
from invoice_extractor import windows

CORPUS = "unit/window_corpus"

MA = ("ma_no_period_v1", "ma_with_period_v1")
USERS: dict[str, tuple[str, ...]] = {
    "MA_HS_LINES_AFTER_ITEM": MA,
    "MA_AK_GROSS_LINES_AFTER_HU": ("ma_ak_billing_v1",),
    "MA_AK_LINES_AFTER_ITEM": ("ma_ak_billing_v1",),
    "MA_WP_COO_INDEX_CHARS": ("ma_with_period_v1",),
    "MA_NP_COO_BLOCK_CHARS": ("ma_no_period_v1",),
    "EBIKE_LINES_AFTER_ITEM": ("ebike_ax_billing_v1",),
    "PT_H3_LINES_AFTER_ITEM": ("pt_dremel_head3_v1",),
    "PT_H5_LINES_AFTER_ITEM": ("pt_dremel_head5_v1",),
    "PT_GLORIA_ORIGIN_HS_LINES": ("pt_gloria_v1",),
    "SOE_ITEM_WINDOW_CHARS": ("soe_rb_gmbh_v1",),
    "SOE_PALLETS_GAP_CHARS": ("soe_rb_gmbh_v1",),
    "BITZER_INVNO_GAP_CHARS": ("bitzer_v1",),
    "BITZER_PRICE_TAIL_CHARS": ("bitzer_v1",),
    "BITZER_FINAL_AMOUNT_CHARS": ("bitzer_v1",),
    "HITACHI_GLS_PKG_LINES": ("hitachi_gls_v1",),
    "HITACHI_GLS_DESC_LINES": ("hitachi_gls_v1",),
    "HITACHI_GLS_PN_LINES": ("hitachi_gls_v1",),
    "HITACHI_GLS_BLOCK_CHARS": ("hitachi_gls_v1",),
    "HITACHI_ASIA_BHC_NO_LINES": ("hitachi_asia_hitt_v1",),
    "NIDEC_DATE_CHARS": ("nidec_v1",),
    "PKL_TOTAL_PALLETS_GAP": ("*pkl",),
    "PKL_GW_LABEL_GAP": ("*pkl",),
}

# Limits measured too tight (fragility audit 2026-11-25 #7 #8; fixed structurally later).
KNOWN_TIGHT: dict[str, str] = {
    "MA_HS_LINES_AFTER_ITEM": "needs 48 of 55 lines (item crossing a page, RBTW 2000271108)",
    "MA_AK_LINES_AFTER_ITEM": "needs 38 of 45 lines (AK00067724 origin+HS on line 37)",
    "HITACHI_GLS_DESC_LINES": "description sits 2 lines under the row; 3 → 2 drops it (MEH6L040)",
}


def test_every_window_constant_is_covered():
    assert set(USERS) == set(windows.ALL)


def _docs():
    path = samples.path(f"{CORPUS}/index.json")
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["documents"]


def _run(name: str, docs: list[dict]) -> dict:
    from invoice_extractor.pairing import parse_packing_pkg_gw
    from invoice_extractor.rules_engine import extract_invoice
    from regression_batches import projection

    root = samples.path(CORPUS)
    users = USERS[name]
    out = {}
    for d in docs:
        text = (root / d["text"]).read_text(encoding="utf-8")
        if users == ("*pkl",):
            out[d["text"]] = parse_packing_pkg_gw(text)
        elif d["format_id"] in users:
            r = extract_invoice(d["source"], text=text, backend="cached", format_id=d["format_id"]).to_dict()
            out[d["text"]] = (projection(r), r["meta"].get("needs_gold_fields"))
    return out


def _params():
    return [
        pytest.param(n, marks=pytest.mark.xfail(reason=KNOWN_TIGHT[n], strict=True)) if n in KNOWN_TIGHT else n
        for n in sorted(windows.ALL)
    ]


@pytest.mark.private_samples(CORPUS)
@pytest.mark.parametrize("name", _params())
def test_limit_has_20_percent_margin(name, monkeypatch):
    require_samples(CORPUS)
    docs = _docs()
    normal = _run(name, docs)
    assert normal, f"no corpus document uses {name}"
    monkeypatch.setattr(windows, name, math.floor(windows.ALL[name] * 0.8))
    shrunk = _run(name, docs)
    moved = sorted(k for k in normal if normal[k] != shrunk[k])
    sources = {d["text"]: d["source"] for d in docs}
    assert not moved, f"{name} at 80% changes {len(moved)} doc(s): " + ", ".join(sources[k] for k in moved[:5])
