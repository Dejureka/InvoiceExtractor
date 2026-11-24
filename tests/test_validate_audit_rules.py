"""Checks for independent totals, packing allocation, and extract status."""
from copy import deepcopy
from decimal import Decimal

import pytest

from test_validate_result import findings, invoice, validate


def packing_invoice(invoice, **units):
    invoice["meta"].update(format_id="ma_no_period_v1", packing_units=units,
                           source_file="batch/shipment/first.pdf")
    invoice["header"].update(total_pkg=len(units), gross_weight_kg=sum(map(Decimal, units.values())))
    return invoice


@pytest.mark.parametrize(("format_id", "prefix", "status"), [
    ("ma_no_period_v1", "H", "hard"),
    ("other_v1", "W", "warn"),
])
def test_packing_count_and_weight(invoice, format_id, prefix, status):
    packing_invoice(invoice, shared="11.604", other="20.12")
    invoice["meta"]["format_id"] = format_id
    assert not validate(extracts=invoice).findings
    invoice["header"].update(total_pkg=3, gross_weight_kg="31.780")
    assert [(f.rule_id, f.status, f.expected) for f in validate(extracts=invoice).findings] == [
        (f"{prefix}_PACKING_UNITS", status, Decimal(2)),
        (f"{prefix}_PACKING_GW", status, Decimal("31.724")),
    ]


def test_packing_rounding_includes_each_keys_printed_precision(invoice):
    packing_invoice(invoice, first="11.604", second="4.00", third=10)
    invoice["header"]["gross_weight_kg"] = "26.1595"
    assert [f.field for f in findings(invoice, "W_ROUNDING")] == ["gross_weight_kg"]
    invoice["header"]["gross_weight_kg"] = "26.1596"
    assert findings(invoice, "H_PACKING_GW")


@pytest.fixture
def shipment_rows(invoice):
    first = packing_invoice(invoice, shared="11.604")
    second = packing_invoice(deepcopy(first), shared="11.604", second="4.23")
    second["header"]["invoice_no"] = "another-invoice"
    second["meta"]["source_file"] = "batch/shipment/second.pdf"
    return first, second


def test_shared_keys_require_shipment_first_in_same_folder(shipment_rows):
    first, second = shipment_rows
    assert [(f.invoice_no, f.status, f.actual) for f in findings(shipment_rows, "H_PACKING_SHARED")] == [
        (row["header"]["invoice_no"], "hard", ["shared"]) for row in shipment_rows
    ]
    second["meta"]["source_file"] = "batch/another-shipment/second.pdf"
    assert not findings(shipment_rows, "H_PACKING_SHARED")
    twin = deepcopy(first)
    twin["meta"]["source_file"] = "batch/shipment/first.xlsx"
    assert not findings([first, twin], "H_PACKING_SHARED")


def test_shipment_first_union_and_shared_keys_zeroed(shipment_rows):
    first, second = shipment_rows
    info = {
        "mode": "shipment_first", "first_invoice": first["header"]["invoice_no"],
        "invoices": [row["header"]["invoice_no"] for row in shipment_rows],
        "total_pkg": 2, "gross_weight_kg": "15.834", "shared_rb": ["shared"],
    }
    for row in shipment_rows:
        row["meta"]["shipment_packing"] = dict(info)
    first["header"].update(total_pkg=2, gross_weight_kg="15.834")
    second["header"].update(total_pkg=0, gross_weight_kg=0)
    second["meta"]["packing_units_zeroed"] = {"shared": "11.604"}
    # Existing rule: a non-first 0 without the shipment note stays hard.
    assert [f.field for f in findings(shipment_rows, "H_HDR_MISSING")] == ["total_pkg", "gross_weight_kg"]
    second["header"]["summary_note"] = f"shipment pkg/GW (deduped) on {first['header']['invoice_no']}"
    assert not validate(extracts=shipment_rows).findings
    assert not validate(extracts=first).findings  # Partial run uses shipment totals.

    second["meta"].pop("packing_units_zeroed")
    assert [f.invoice_no for f in findings(shipment_rows, "H_PACKING_SHARED")] == [
        second["header"]["invoice_no"]
    ]
    second["header"]["total_pkg"] = 1
    assert [f.field for f in findings(shipment_rows, "H_PRINTED_PACKING")] == ["total_pkg"]
    assert not findings(shipment_rows, "H_PACKING_UNITS")

    # The unit union remains independent of the stored shipment total.
    first["header"]["total_pkg"] = first["meta"]["shipment_packing"]["total_pkg"] = 1
    assert [f.expected for f in findings(shipment_rows, "H_PACKING_UNITS")] == [Decimal(2)]
    assert not findings(first, "H_PACKING_UNITS")


def test_printed_qty_and_mixed_units(invoice):
    line = invoice["items"][0]
    line["unit"] = "pc."
    invoice["items"] += [dict(line, item_no=2, unit="PCS"), dict(line, item_no=3, unit="pcs")]
    invoice["header"]["total_quantity"] = 4
    assert [(f.status, f.expected, f.actual) for f in findings(invoice, "H_PRINTED_QTY")] == [
        ("hard", Decimal(4), Decimal(3))
    ]
    invoice["items"][-1]["unit"] = "cartons"
    assert [f.status for f in findings(invoice, "W_PRINTED_QTY_MIXED_UOM")] == ["warn"]
    assert not findings(invoice, "H_PRINTED_QTY")
    invoice["header"]["total_quantity"] = 3
    assert not findings(invoice, "W_PRINTED_QTY_MIXED_UOM")
    assert not findings(invoice, "H_PRINTED_QTY")


def test_explicit_printed_qty_precedence_and_fractional_tolerance(invoice):
    invoice["items"][0]["qty"] = "1.250"
    invoice["header"]["total_quantity"] = 2
    invoice["meta"].update(printed_total_quantity=None, labeled_quantity="1.2505", labeled_total_quantity=3)
    assert not findings(invoice, "H_PRINTED_QTY")
    invoice["meta"]["printed_total_quantity"] = "1.2506"
    assert findings(invoice, "H_PRINTED_QTY")
    invoice["items"][0]["qty"] = "1.000"
    invoice["meta"]["printed_total_quantity"] = "1.0001"
    assert findings(invoice, "H_PRINTED_QTY")


def test_labeled_amount_coverage_warning(invoice):
    assert not findings(invoice, "W_NO_LABELED_TOTAL")
    invoice["meta"]["labeled_amount_label"] = "sum(lines)"
    assert len(findings(invoice, "W_NO_LABELED_TOTAL")) == 1
    invoice["meta"].pop("labeled_amount")
    warning, = findings(invoice, "W_NO_LABELED_TOTAL")
    assert warning.status == "warn" and warning.field == "amount"
    assert "qty total not independently verifiable" in warning.note
    invoice["meta"]["printed_total_quantity"] = 1
    warning, = findings(invoice, "W_NO_LABELED_TOTAL")
    assert warning.note == "no printed amount total captured"
    assert not findings(invoice, "W_LINE_COUNT_UNVERIFIED")


def test_excel_twin_uses_pdf_twin_printed_total(invoice):
    pdf = deepcopy(invoice)
    pdf["meta"].update(source_file="case/IV_1.PDF", labeled_amount=10.25, labeled_amount_label="TOTAL")
    xlsx = deepcopy(invoice)
    xlsx["meta"].update(source_file="case/IV_1.xlsx", labeled_amount=10.25,
                        labeled_amount_label="sum(lines) (xlsx twin; no TOTAL row)")
    assert not findings([pdf, xlsx], "W_NO_LABELED_TOTAL")
    xlsx["items"][0]["amount"] = xlsx["header"]["amount"] = 9.25
    xlsx["items"][0]["unit_price"] = 9.25
    printed, = findings([pdf, xlsx], "H_PRINTED_AMOUNT")
    assert printed.expected == Decimal("10.25") and "from twin" in printed.note
    assert len(findings(xlsx, "W_NO_LABELED_TOTAL")) == 1  # No twin: coverage gap stays visible.


@pytest.mark.parametrize("meta", [
    {"text_backend": "poppler+ocr_failed"},
    {"text_backend": "ocr_timeout"},
    {"ocr_error": "Command 'tesseract' timed out after 60 seconds"},
    {"needs_ocr": True},
])
def test_ocr_failure(invoice, meta):
    assert not findings(invoice, "H_OCR_FAILED")
    invoice["meta"].update(meta, needs_gold_fields=["text_backend"], needs_gold=True)
    failure, = findings(invoice, "H_OCR_FAILED")
    assert failure.status == "hard"
    assert "NOT validated against text" in failure.note


def test_bl_ocr_status(invoice):
    bill = {"header": {"hbl_no": "bill"}, "meta": {"text_backend": "image+ocr_failed"}, "items": []}
    failure, = validate(extracts=invoice, bl_extracts=bill).findings
    assert (failure.rule_id, failure.field, failure.invoice_no) == ("H_OCR_FAILED", "bl_no", "bill")
    bill["doc_type"] = "bl"
    assert [f.rule_id for f in validate(extracts=[invoice, bill]).findings] == ["H_OCR_FAILED"]


def test_needs_gold_flags(invoice):
    invoice["meta"].update(needs_gold=False, needs_gold_fields=["header.amount"])
    assert [f.status for f in findings(invoice, "H_NEEDS_GOLD_FLAG")] == ["hard"]
    invoice["meta"].update(needs_gold=True, checker_verdict="pass")
    assert findings(invoice, "H_NEEDS_GOLD_FLAG")
    invoice["meta"]["checker_verdict"] = "ok"
    assert findings(invoice, "H_NEEDS_GOLD_FLAG")
    invoice["meta"]["checker_verdict"] = "needs_gold"
    assert not findings(invoice, "H_NEEDS_GOLD_FLAG")
    assert not findings(invoice, "W_NEEDS_GOLD_FLAG")
    invoice["meta"]["needs_gold_fields"] = []
    assert [f.status for f in findings(invoice, "W_NEEDS_GOLD_FLAG")] == ["warn"]


@pytest.mark.parametrize("key", ["printed_item_count", "printed_line_count", "item_count_printed"])
def test_printed_line_count_and_summary_consistency(invoice, key):
    invoice["meta"][key] = 2
    invoice["header"]["item_line_count"] = 3
    summary, printed = findings(invoice, "H_LINE_COUNT")
    assert (summary.expected, summary.actual, summary.note) == (
        Decimal(3), Decimal(1), "Summary item_line_count vs Lines rows"
    )
    assert (printed.expected, printed.actual, printed.status) == (Decimal(2), Decimal(1), "hard")


def count_unverified(invoice):
    """W_LINE_COUNT_UNVERIFIED, or its text folded into W_NO_LABELED_TOTAL (one warn per row)."""
    return findings(invoice, "W_LINE_COUNT_UNVERIFIED") + [
        f for f in findings(invoice, "W_NO_LABELED_TOTAL")
        if "line count not independently verifiable" in f.note
    ]


@pytest.mark.parametrize("step", [1, 10])
def test_continuous_positions_provide_count(invoice, step):
    del invoice["meta"]["labeled_amount"]
    line = invoice["items"][0]
    line["item_no"] = step
    invoice["items"].append(dict(line, item_no=2 * step))
    invoice["header"]["item_line_count"] = 2
    assert not count_unverified(invoice)
    invoice["items"][1]["item_no"] = 3 * step
    assert findings(invoice, "H_LINE_POS")
    assert count_unverified(invoice)


def test_line_count_warns_only_without_independent_count_or_printed_total(invoice):
    del invoice["items"][0]["item_no"]
    assert not count_unverified(invoice)
    del invoice["meta"]["labeled_amount"]
    invoice["header"]["total_quantity"] = 1
    assert count_unverified(invoice)
    invoice["header"]["total_quantity"] = 2
    assert not count_unverified(invoice)
    invoice["header"]["total_quantity"] = 1
    invoice["meta"]["printed_total_quantity"] = 1
    assert not count_unverified(invoice)
    del invoice["meta"]["printed_total_quantity"]
    invoice["meta"]["printed_item_count"] = 1
    assert not count_unverified(invoice)
