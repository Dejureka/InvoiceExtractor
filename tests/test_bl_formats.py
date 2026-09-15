"""BL / arrival-notice format families (BHC cases 2–6 text layer)."""

from __future__ import annotations

from pathlib import Path

import pytest

from invoice_extractor.bl_rules_engine import classify_bl, extract_bl, looks_like_bl_filename
from invoice_extractor.checker_bl import hard_check_bl

ROOT = Path("/workspace/bhc_cases_round/bhc")
TEXT = Path("/workspace/bhc_bl_text")

SAMPLES = [
    (
        "case2",
        "到貨通知 - NGOA23259.pdf",
        "dhl_lcl_arrival_v1",
        "NGOA23259",
    ),
    (
        "case3",
        "HBL draft HB26090012 KTMBE26080067.pdf",
        "hippopo_hbl_v1",
        "HB26090012",
    ),
    ("case4", "到貨 448.pdf", "ceva_pyramid_arrival_v1", "WEB260166448"),
    ("case5", "到貨 449.pdf", "ceva_pyramid_arrival_v1", "WEB260166449"),
    ("case6", "到貨 298.pdf", "ceva_pyramid_arrival_v1", "WEB260169298"),
]


@pytest.mark.parametrize("case,fname,fmt,bl", SAMPLES)
def test_classify_and_extract(case, fname, fmt, bl):
    pdf = ROOT / case / fname
    if not pdf.is_file():
        pytest.skip(f"missing {pdf}")
    result = extract_bl(pdf)
    data = result.to_dict()
    assert data["meta"]["format_id"] == fmt
    h = data["header"]
    assert (h.get("bl_no") or h.get("hbl_no")) == bl
    hard = hard_check_bl(data)
    assert hard["verdict"] == "pass", hard


def test_ceva_family_shared():
    """Cases 4/5/6 share one layout family, not one-per-forwarder-id."""
    ids = set()
    for stem in ("到貨 448", "到貨 449", "到貨 298"):
        text = (TEXT / f"{stem}.txt").read_text(encoding="utf-8", errors="replace")
        fid, score = classify_bl(text, f"{stem}.pdf")
        assert fid == "ceva_pyramid_arrival_v1"
        assert score >= 0.5
        ids.add(fid)
    assert ids == {"ceva_pyramid_arrival_v1"}


def test_looks_like_bl_filename():
    assert looks_like_bl_filename("到貨 448.pdf")
    assert looks_like_bl_filename("HBL draft HB26090012.pdf")
    assert looks_like_bl_filename("到貨通知 - NGOA23259.pdf")
    assert not looks_like_bl_filename("TA2608B2_INV_9027451705.PDF")
