"""Shared fallback marker: value unchanged, note always, flag only in step B."""
from __future__ import annotations

from invoice_extractor import fallback as fb
from invoice_extractor.schema import Meta


def test_fallback_returns_value_and_ignores_empty():
    with fb.collecting() as hits:
        assert fb.fallback("total_pkg", 3.0, "r1") == 3.0
        assert fb.fallback("gross_weight_kg", None, "r2") is None
        assert fb.fallback("invoice_no", "", "r3") == ""
        fb.fallback("total_pkg", 3.0, "r1")
    assert hits == [("total_pkg", "r1")]


def test_outside_collecting_is_a_no_op():
    assert fb.fallback("total_pkg", 1.0, "r") == 1.0


def test_record_note_only_when_flag_off(monkeypatch):
    monkeypatch.setattr(fb, "FLAG_FALLBACKS", False)
    meta = Meta(notes="x")
    fb.record(meta, [("gross_weight_kg", "r")])
    assert meta.notes == "x; fallback[gross_weight_kg]=r"
    assert meta.needs_gold_fields is None and meta.needs_gold is False


def test_record_flags_field_when_flag_on(monkeypatch):
    monkeypatch.setattr(fb, "FLAG_FALLBACKS", True)
    meta = Meta(needs_gold_fields=["total_pkg"])
    fb.record(meta, [("total_pkg", "a"), ("gross_weight_kg", "b")])
    assert meta.needs_gold_fields == ["total_pkg", "gross_weight_kg"]
    assert meta.needs_gold is True and meta.confidence == "needs_gold"


def test_fields_outside_result_stay_note_only(monkeypatch):
    monkeypatch.setattr(fb, "FLAG_FALLBACKS", True)
    meta = Meta()
    fb.record(meta, [("invoice_date", "r")])
    assert meta.notes == "fallback[invoice_date]=r"
    assert meta.needs_gold_fields is None and meta.needs_gold is False


def test_step_b_is_on():
    assert fb.FLAG_FALLBACKS is True


def test_unanchored_rule_leaves_a_note_through_apply_format():
    from invoice_extractor.rules_engine import apply_format

    # Synthetic dunan-like PL: no labelled GW, only an unlabelled "GW NW CBM" triple.
    text = (
        "ZHEJIANG DUNAN INTERNATIONAL TRADING CO.,LTD.\nPACKING LIST\n"
        "INVOICE NO.: FT00000001\nTOTAL: 2 PALLETS\n 1234.50 1100.00 2.5\n"
    )
    r = apply_format("dunan_v1", "x.pdf", text, "provided", False)
    assert r.header.gross_weight_kg == 1234.5
    assert "fallback[gross_weight_kg]=dunan:first_weight_pair_anywhere" in (r.meta.notes or "")
    assert r.meta.needs_gold_fields == ["gross_weight_kg"]
