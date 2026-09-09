from invoice_extractor.schema import ExtractResult, Header, Item, Meta, eu_float, us_float, de_date_to_iso


def test_eu_float():
    assert eu_float("6.052,400") == 6052.4
    assert eu_float("10.583,26") == 10583.26


def test_us_float():
    assert us_float("1,003.28") == 1003.28
    assert us_float("10,091.68") == 10091.68


def test_de_date():
    assert de_date_to_iso("04.12.2025") == "2025-12-04"


def test_roundtrip_dict():
    r = ExtractResult(
        header=Header(invoice_no="1", amount=1.0, currency="USD"),
        items=[Item(invoice_no="1", part_no="x", qty=1, amount=1.0)],
        meta=Meta(source_file="a.pdf", format_id="t"),
    )
    d = r.to_dict()
    assert d["header"]["invoice_no"] == "1"
    assert len(d["items"]) == 1
