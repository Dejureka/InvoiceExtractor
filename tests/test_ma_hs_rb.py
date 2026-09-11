"""MA HS look-ahead + unique RB packing helpers."""

from __future__ import annotations

from invoice_extractor.formats.ma_common import find_hs_after_item, parse_rb_packages
from invoice_extractor.formats import ma_with_period_v1 as wp


def test_find_hs_past_many_dispatch_elements():
    lines = [
        "00040 1.987.479.202.GEH    Brake Fluid                                   1,800 EA               178 *            320,400",
        "                           Weight                                         2,160 kg",
        "                           Dispatch element:200317617                      360 EA",
        "                           Dispatch element:200317609                      360 EA",
        "                           Dispatch element:200317611                      360 EA",
        "                           Dispatch element:200317612                      360 EA",
        "                           Dispatch element:200317613                      360 EA",
        "       1987479202GEH/4047025681995",
        "                           HS CODE 38190000",
        "00050 1.987.479.207.GEH    Brake Fluid                                     906 EA               180 *            163,080",
    ]
    assert find_hs_after_item(lines, 0) == "38190000"


def test_parse_rb_unique():
    text = """
RB 200317606     Packing Set 1200X800X1000    1,200/800/960MM      Gross       541.000    KG
RB 200317608     Packing Set 1200X800X1000    1,200/800/960MM      Gross       541.000    KG
RB 200317606     Packing Set 1200X800X1000    1,200/800/960MM      Gross       541.000    KG
RB 200317619     Corrugated carton            326/226/170MM        Gross        0.760     KG
"""
    pkg, gw = parse_rb_packages(text)
    assert pkg == 3.0
    assert gw == 1082.76


def test_line_regex_geh():
    line = "00040 1.987.479.202.GEH    Brake Fluid                                   1,800 EA               178 *            320,400"
    m = wp._LINE.match(line)
    assert m
    assert m.group("pn") == "1.987.479.202.GEH"
    assert m.group("qty") == "1,800"
