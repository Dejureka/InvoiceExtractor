"""MA NoPeriod Country Of Origin Index parser hardening."""

from __future__ import annotations

from invoice_extractor.formats import ma_no_period_v1 as np


def test_coo_skips_empty_header_only_page():
    """First Index page is footer-only; rows live on the next Index page."""
    text = """
Country Of Origin            Index
Bank account: Deutsche Bank AG, IBAN: DE32
Page 14 of 18
\x0c
Country Of Origin            Index
Japan                         3CA
Japan                        TT1


Country Of Origin
                              HS CODE
                               8413910002
"""
    m = np._parse_coo_index(text)
    assert m == {"3CA": "Japan", "TT1": "Japan"}


def test_coo_multipage_continues_after_bank_footer():
    text = """
Country Of Origin            Index
Germany                       000
Germany                      KVS
Bank account: Deutsche Bank AG
Page 38 of 57
\x0c
Country Of Origin            Index
China                         WA2
China                        WGP


Country Of Origin
                              HS CODE
"""
    m = np._parse_coo_index(text)
    assert m["000"] == "Germany"
    assert m["KVS"] == "Germany"
    assert m["WA2"] == "China"
    assert m["WGP"] == "China"


def test_coo_unicode_turkiye():
    text = """
Country Of Origin            Index
Türkiye                      825
China                        879

Country Of Origin
"""
    m = np._parse_coo_index(text)
    assert m["825"] == "Türkiye"
    assert m["879"] == "China"
    assert "rkiye" not in m.values()


def test_origin_applied_from_pn_suffix():
    text = """
000010 1986S00652WGP                 Alternator                                           1 EA                  100.00 *              100
                                     Weight                                                    1.000 KG
                                     HS CODE        8511503200

Country Of Origin            Index
China                        WGP

Country Of Origin
"""
    r = np.extract_from_text(text, source_file="t.pdf")
    assert len(r.items) == 1
    assert r.items[0].origin == "China"
