"""hitachi_gls header by position (label row → value row), not by the MEH prefix (synthetic)."""
from __future__ import annotations

from invoice_extractor.rules_engine import apply_format

HDR = (
    "HITACHI GLOBAL LIFE SOLUTIONS, INC.\n"
    "Sold by Order and for account and Risk of Messrs.      Invoice No.            Date\n"
    " BOSCH HOME COMFORT TAIWAN CO., LTD.                    {no}               {date}\n"
    "SERVICE PARTS                 GRAND TOTAL:   145 PCS          {total}\n"
)


def _run(no, date, total):
    return apply_format("hitachi_gls_v1", "x.pdf", HDR.format(no=no, date=date, total=total), "provided", False)


def test_meh_series_unchanged():
    r = _run("MEH6K018", "OCT. 05, 2026", "J¥1,234,000")
    h = r.header
    assert (h.invoice_no, h.invoice_date, h.amount, h.currency) == ("MEH6K018", "2026-10-05", 1234000.0, "JPY")
    assert "invoice_no" not in (r.meta.needs_gold_fields or [])


def test_other_series_read_by_position_and_flagged():
    r = _run("DC76K507", "NOV. 06, 2026", "US$2,449.00")
    h = r.header
    assert (h.invoice_no, h.invoice_date, h.amount, h.currency) == ("DC76K507", "2026-11-06", 2449.0, "USD")
    assert "invoice_no" in r.meta.needs_gold_fields
