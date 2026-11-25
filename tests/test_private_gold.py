"""Gold for formats that had no frozen coverage (kept private: real invoices).

/workspace/invoice-samples/gold/cov8.json lists single documents, the Result
values they must produce, and fields deliberately NOT frozen ("excluded",
with the reason) because they looked wrong when the gold was checked.
Formats: aichi_electric, bhc_manual_inv, hitachi_asia_hitt, ohizumi_dongguan,
oukai, sumitronics_hk (invoices); dhl_danmar_bl, nippon_express_awb (BL).
"""
from __future__ import annotations

import json

import pytest

import samples
from conftest import require_samples
from regression_batches import projection

GOLD_REL = "gold/cov8.json"


def _gold():
    path = samples.path(GOLD_REL)
    if not path.is_file():
        return []
    return json.loads(path.read_text(encoding="utf-8"))["documents"]


def _round(v):
    if isinstance(v, float):
        return round(v, 6)
    if isinstance(v, dict):
        return {k: _round(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_round(x) for x in v]
    return v


def _ids():
    return [d["file"].rsplit("/", 2)[-2] + "/" + d["file"].rsplit("/", 1)[-1] for d in _gold()] or ["no-gold"]


@pytest.mark.private_samples(GOLD_REL)
@pytest.mark.parametrize("doc", _gold() or [None], ids=_ids())
def test_private_gold(doc):
    assert doc is not None, "gold/cov8.json has no documents"
    path, = require_samples(doc["file"])
    excluded = doc.get("excluded") or {}
    if doc["kind"] == "bl":
        from invoice_extractor.bl_rules_engine import extract_bl

        d = extract_bl(path).to_dict()
        assert d["meta"]["format_id"] == doc["format_id"]
        h = d["header"]
        got = {k: h.get(k) for k in doc["bl"]}
        assert _round(got) == _round(doc["bl"])
        return
    from invoice_extractor.rules_engine import extract_invoice

    d = extract_invoice(path).to_dict()
    assert d["meta"]["format_id"] == doc["format_id"]
    pr = projection(d)
    summary = {k: v for k, v in pr["header"].items() if k not in excluded}
    assert _round(summary) == _round(doc["summary"])
    if doc["lines"] is not None:
        assert _round(pr["items"]) == _round(doc["lines"])
