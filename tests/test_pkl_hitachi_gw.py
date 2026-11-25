"""Generic PKL "(TOTAL: N PALLETS" branch reads GW from the weight columns, never a case value."""
from __future__ import annotations

from invoice_extractor.pairing import parse_packing_pkg_gw

HEAD = "PACKING LIST\nSETS KGS. CLM.\n"


def test_single_item_row():
    t = HEAD + "P1 INDUCTION MOTOR 38 977.50 1,174.00 1.556\n(TOTAL: 2 PALLETS ONLY)\n"
    assert parse_packing_pkg_gw(t) == (2.0, 1174.0)


def test_other_weight_is_not_special_cased():
    t = HEAD + "P1 MOTOR 10 400.00 455.25 0.800\n(TOTAL: 1 PALLET ONLY)\n"
    assert parse_packing_pkg_gw(t) == (1.0, 455.25)


def test_item_rows_are_summed():
    rows = "P1 MOTOR 10 400.00 455.25 0.800\nP2 MOTOR 5 100.00 120.75 0.300\n"
    assert parse_packing_pkg_gw(HEAD + rows + "(TOTAL: 3 PALLETS ONLY)\n") == (3.0, 576.0)


def test_no_weight_row_means_no_guess():
    t = HEAD + "weights 977.50 and 1,174.00 somewhere\n(TOTAL: 2 PALLETS ONLY)\n"
    assert parse_packing_pkg_gw(t) == (2.0, None)
