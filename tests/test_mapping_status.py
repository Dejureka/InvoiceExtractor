"""Tests for format-mapping status helper."""

from __future__ import annotations

from invoice_extractor.mapping_status import (
    LABEL_AUDIT_OK,
    LABEL_HARD_FAIL,
    LABEL_KNOWN_UNAUDITED,
    LABEL_NEW_NEEDS_RULES,
    checker_display,
    count_mapping_statuses,
    format_status_line,
    load_audited_format_ids,
    mapping_status,
)


def test_audited_registry_contains_round4_set():
    ids = load_audited_format_ids()
    for fid in (
        "pt_gloria_v1",
        "bitzer_v1",
        "hangji_v1",
        "nidec_v1",
        "hitachi_gls_v1",
        "highly_v1",
        "ma_with_period_v1",
        "ma_no_period_v1",
        "bhc_my_hub_v1",
    ):
        assert fid in ids, fid


def test_mapping_audit_ok():
    assert (
        mapping_status({"format_id": "pt_gloria_v1"}, "pass") == LABEL_AUDIT_OK
    )


def test_mapping_known_unaudited():
    assert (
        mapping_status(
            {"format_id": "future_vendor_v1"},
            "pass",
            audited_ids=frozenset({"pt_gloria_v1"}),
        )
        == LABEL_KNOWN_UNAUDITED
    )


def test_mapping_new_needs_rules_no_format():
    assert mapping_status({}, "needs_gold") == LABEL_NEW_NEEDS_RULES
    assert mapping_status({"needs_gold": True}, "pass") == LABEL_NEW_NEEDS_RULES
    assert mapping_status({"needs_ocr": True, "format_id": None}, None) == LABEL_NEW_NEEDS_RULES
    assert (
        mapping_status({"format_id": None, "confidence": "needs_gold"}, "pass")
        == LABEL_NEW_NEEDS_RULES
    )


def test_mapping_hard_fail_overrides_audit():
    assert (
        mapping_status({"format_id": "pt_gloria_v1"}, "conflict") == LABEL_HARD_FAIL
    )


def test_checker_display_and_status_line():
    assert checker_display("pass") == "hard pass"
    assert checker_display("conflict") == "hard fail"
    line = format_status_line(
        invoice_no="50666223",
        format_id="pt_gloria_v1",
        mapping=LABEL_AUDIT_OK,
        checker_verdict="pass",
    )
    assert line == "50666223 | pt_gloria_v1 | audit ok | hard pass"


def test_count_mapping_statuses():
    counts = count_mapping_statuses(
        [LABEL_AUDIT_OK, LABEL_AUDIT_OK, LABEL_NEW_NEEDS_RULES, LABEL_HARD_FAIL]
    )
    assert counts[LABEL_AUDIT_OK] == 2
    assert counts[LABEL_NEW_NEEDS_RULES] == 1
    assert counts[LABEL_HARD_FAIL] == 1
    assert counts[LABEL_KNOWN_UNAUDITED] == 0
