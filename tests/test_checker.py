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


def test_labeled_total_catches_under_extract():
    """1×5291.63 must FAIL when Final amount / labeled_amount is present.

    Circular header.amount == sum(items) alone must not pass.
    """
    extract = {
        "header": {
            "invoice_no": "200167553",
            "amount": 5291.63,  # wrongly set from incomplete sum
            "currency": "EUR",
            "item_line_count": 1,
            "total_quantity": 1,
        },
        "items": [
            {
                "qty": 1,
                "unit_price": 5291.63,
                "amount": 5291.63,
                "currency": "EUR",
            }
        ],
        "meta": {
            "labeled_amount": 37041.41,
            "labeled_amount_label": "Final amount",
        },
    }
    r = hard_check(extract)
    assert r["verdict"] == "conflict"
    assert any("labeled" in i for i in r["issues"])
    assert r["details"]["labeled_amount"]["want"] == 37041.41


def test_labeled_total_pass_when_complete():
    extract = {
        "header": {
            "invoice_no": "200167553",
            "amount": 37041.41,
            "currency": "EUR",
            "item_line_count": 5,
            "total_quantity": 7,
        },
        "items": [
            {"qty": 2, "unit_price": 5291.63, "amount": 10583.26, "currency": "EUR"},
            {"qty": 2, "unit_price": 5291.63, "amount": 10583.26, "currency": "EUR"},
            {"qty": 1, "unit_price": 5291.63, "amount": 5291.63, "currency": "EUR"},
            {"qty": 1, "unit_price": 5291.63, "amount": 5291.63, "currency": "EUR"},
            {"qty": 1, "unit_price": 5291.63, "amount": 5291.63, "currency": "EUR"},
        ],
        "meta": {
            "labeled_amount": 37041.41,
            "labeled_amount_label": "Final amount",
        },
    }
    r = hard_check(extract)
    assert r["verdict"] == "pass"
    assert r["details"]["labeled_amount"]["want"] == 37041.41
