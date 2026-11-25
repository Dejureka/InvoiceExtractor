"""Count words + dunan packing totals without case values (synthetic text)."""
from __future__ import annotations

import pytest

from invoice_extractor.formats.dunan_v1 import extract_from_text
from invoice_extractor.numwords import en_count


@pytest.mark.parametrize("word,n", [("EIGHT", 8), ("twenty-two", 22), ("THIRTY FOUR", 34),
                                    ("NINETEEN", 19), ("NINETY-NINE", 99), ("TWENTY-TEN", None), ("PALLET", None)])
def test_en_count(word, n):
    assert en_count(word) == n


HEAD = "ZHEJIANG DUNAN INTERNATIONAL TRADING CO.,LTD.\nINVOICE NO.: DA1/2\n"


def test_total_row_gives_gw_not_first_pallet_group():
    text = HEAD + (
        "   C/NO:1-4   4PALLETS     644.00   504.00   1.52\n"
        "   C/NO:2-8   8PALLETS    2764.00  2389.00   8.33\n"
        "                 44644 PCS       9526.00         8405.00            38.16\n"
        "                     TOTAL:34PALLETS\n"
    )
    h = extract_from_text(text).header
    assert (h.total_pkg, h.gross_weight_kg) == (34.0, 9526.0)


def test_packed_in_words_when_no_total_row():
    h = extract_from_text(HEAD + "PACKED IN THIRTEEN PALLETS ONLY\n").header
    assert h.total_pkg == 13.0
