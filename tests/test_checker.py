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



def test_ma_requires_line_hs():
    """MA: one missing HS → conflict (not soft)."""
    extract = {
        "header": {
            "invoice_no": "2000262902",
            "amount": 30.0,
            "currency": "TWD",
            "item_line_count": 2,
            "total_quantity": 3,
        },
        "items": [
            {
                "qty": 1,
                "unit_price": 10,
                "amount": 10,
                "currency": "TWD",
                "hs_code": "38190000",
            },
            {
                "qty": 2,
                "unit_price": 10,
                "amount": 20,
                "currency": "TWD",
                "hs_code": None,
            },
        ],
        "meta": {"format_id": "ma_no_period_v1"},
    }
    r = hard_check(extract)
    assert r["verdict"] == "conflict"
    assert any("hs_code" in i for i in r["issues"])


def test_pt_requires_line_hs():
    extract = {
        "header": {
            "invoice_no": "50656407",
            "amount": 10.0,
            "currency": "EUR",
            "item_line_count": 1,
            "total_quantity": 1,
        },
        "items": [
            {
                "qty": 1,
                "unit_price": 10,
                "amount": 10,
                "currency": "EUR",
                "hs_code": "",
            }
        ],
        "meta": {"format_id": "pt_gloria_v1"},
    }
    r = hard_check(extract)
    assert r["verdict"] == "conflict"
    assert any("hs_code" in i for i in r["issues"])


def test_bhc_missing_hs_still_ok():
    """BHC MY-HUB: HS often absent — do not hard-fail on missing HS alone."""
    extract = {
        "header": {
            "invoice_no": "9027451705",
            "amount": 10.0,
            "currency": "USD",
            "item_line_count": 1,
            "total_quantity": 1,
        },
        "items": [
            {
                "qty": 1,
                "unit_price": 10,
                "amount": 10,
                "currency": "USD",
                "hs_code": None,
            }
        ],
        "meta": {"format_id": "bhc_my_hub_v1"},
    }
    r = hard_check(extract)
    assert r["verdict"] == "pass"


def test_ma_all_hs_present_passes():
    extract = {
        "header": {
            "invoice_no": "2000262902",
            "amount": 10.0,
            "currency": "TWD",
            "item_line_count": 1,
            "total_quantity": 1,
        },
        "items": [
            {
                "qty": 1,
                "unit_price": 10,
                "amount": 10,
                "currency": "TWD",
                "hs_code": "38190000",
            }
        ],
        "meta": {"format_id": "ma_with_period_v1"},
    }
    r = hard_check(extract)
    assert r["verdict"] == "pass"


def test_line_amount_relative_tol_commercial_net():
    """Bosch AK Net Value can differ ~0.1% from Unit Price × Qty."""
    extract = {
        "header": {
            "invoice_no": "AK00067730",
            "amount": 18182.0 + 7973.0,
            "currency": "TWD",
            "item_line_count": 2,
            "total_quantity": 85,
        },
        "items": [
            # 35*228=7980 vs net 7973 (diff 7 ≈ 0.088%)
            {"qty": 35, "unit_price": 228, "amount": 7973, "currency": "TWD", "hs_code": "8708309000"},
            # 50*364=18200 vs net 18182 (diff 18 ≈ 0.099%)
            {"qty": 50, "unit_price": 364, "amount": 18182, "currency": "TWD", "hs_code": "8708309000"},
        ],
        "meta": {
            "format_id": "ma_ak_billing_v1",
            "labeled_amount": 18182.0 + 7973.0,
            "labeled_amount_label": "Net value",
        },
    }
    r = hard_check(extract)
    assert r["verdict"] == "pass", r


def test_line_amount_still_flags_large_mismatch():
    extract = {
        "header": {"invoice_no": "X", "amount": 100.0, "currency": "TWD"},
        "items": [
            {"qty": 10, "unit_price": 10, "amount": 50, "currency": "TWD"},  # 50% off → fail
        ],
        "meta": {},
    }
    r = hard_check(extract)
    assert r["verdict"] == "conflict"
    assert any("unit_price*qty" in i for i in r["issues"])
