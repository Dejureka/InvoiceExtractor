"""MA HS look-ahead ends at the next item row, not at a fixed line count (synthetic)."""
from __future__ import annotations

from invoice_extractor.formats.ma_common import find_hs_after_item

ITEM = "00010 F.01R.00A.067"
NEXT = "00020 F.01R.00A.068"


def test_hs_far_below_item_across_pages_is_found():
    lines = [ITEM] + ["  page footer / header noise"] * 120 + ["  HS CODE 85044090"]
    assert find_hs_after_item(lines, 0) == "85044090"


def test_hs_of_next_item_is_never_taken():
    lines = [ITEM, "  Weight 1 KG", NEXT, "  HS CODE 85044090"]
    assert find_hs_after_item(lines, 0) is None
