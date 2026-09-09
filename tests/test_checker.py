from invoice_extractor.checker import hard_check


def test_pass_simple():
    extract = {
        "header": {
            "invoice_no": "1",
            "item_line_count": 2,
            "total_quantity": 3,
            "amount": 30.0,
            "currency": "USD",
        },
        "items": [
            {"qty": 1, "unit_price": 10, "amount": 10, "currency": "USD"},
            {"qty": 2, "unit_price": 10, "amount": 20, "currency": "USD"},
        ],
        "meta": {},
    }
    r = hard_check(extract)
    assert r["verdict"] == "pass"


def test_amount_conflict():
    extract = {
        "header": {"invoice_no": "1", "amount": 100.0, "currency": "USD"},
        "items": [{"qty": 1, "unit_price": 10, "amount": 10, "currency": "USD"}],
        "meta": {},
    }
    r = hard_check(extract)
    assert r["verdict"] == "conflict"
