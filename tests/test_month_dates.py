"""dunan / oukai invoice dates: any month, not only September (synthetic text)."""
from __future__ import annotations

import pytest

from invoice_extractor.formats.dunan_v1 import extract_from_text as dunan
from invoice_extractor.formats.oukai_v1 import extract_from_text as oukai

MONTHS = ["Jan", "Feb.", "March", "Apr", "May", "Jun", "July", "Aug", "Sep", "Sept", "Oct.", "November", "Dec"]


@pytest.mark.parametrize("mon", MONTHS)
def test_dunan_any_month(mon):
    t = f"ZHEJIANG DUNAN INTERNATIONAL TRADING CO.,LTD.\nINVOICE NO.: DA1\nDATE: {mon} 26,2026\n"
    assert dunan(t).header.invoice_date == f"{mon} 26,2026"


@pytest.mark.parametrize("mon", MONTHS)
def test_oukai_any_month(mon):
    t = f"OUKAI\nInvoice No.: OK20261021\nDate: {mon} 21st, 2026\n"
    assert oukai(t).header.invoice_date == f"{mon} 21st, 2026"
