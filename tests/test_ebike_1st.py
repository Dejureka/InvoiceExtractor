"""eBike 1st batch: Energy and Body Systems Kft Billing Document AX…."""

from __future__ import annotations

from pathlib import Path

from invoice_extractor.checker import hard_check
from invoice_extractor.formats import ebike_ax_billing_v1, ma_ak_billing_v1
from invoice_extractor.formats.ebike_ax_billing_v1 import ebike_float, extract_from_text
from invoice_extractor.rules_engine import classify

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ebike_1st"

# Hand-read from pdftotext -layout: invoice_no, lines, Net value EUR, pkg, GW kg, missing HS count.
GOLD = {
    "AX00011132": (3, 10870.85, 1.0, 109.0, 0),
    "AX00011133": (2, 4074.81, 1.0, 90.0, 0),
    "AX00011134": (3, 3051.77, 1.0, 108.0, 0),
    "AX00011135": (9, 23249.10, 1.0, 134.0, 0),
    "AX00011136": (26, 4377.33, 1.0, 121.0, 0),
    "AX00011137": (2, 9227.81, 1.0, 35.0, 0),
    "AX00011138": (2, 4224.08, 1.0, 121.0, 0),
    "AX00011139": (1, 4505.61, 1.0, 107.0, 0),
    "AX00011140": (3, 4246.87, 1.0, 85.0, 0),
    "AX00011141": (1, 6440.14, 1.0, 178.0, 0),
    "AX00011142": (2, 6683.13, 1.0, 195.0, 0),
    "AX00011143": (2, 8519.09, 1.0, 208.0, 0),
    "AX00011144": (1, 6398.88, 1.0, 195.0, 1),
    "AX00011145": (1, 5484.75, 1.0, 166.0, 1),
    "AX00011146": (3, 6243.05, 1.0, 185.0, 0),
    "AX00011147": (2, 7577.14, 1.0, 223.0, 0),
    "AX00011148": (13, 3958.82, 1.0, 89.0, 1),
    "AX00011149": (2, 3447.26, 1.0, 97.0, 0),
}

MISSING_HS = {
    "AX00011144": ["EB12.100.076-VE4"],
    "AX00011145": ["EB12.100.076-VE4"],
    "AX00011148": ["EB13.900.025-VE4"],
}


def _text(inv: str) -> str:
    return (FIXTURES / f"{inv}_layout.txt").read_text()


def test_ebike_float_eu_thousands_and_decimals():
    assert ebike_float("18.022,42") == 18022.42
    assert ebike_float("4.505,61") == 4505.61
    assert ebike_float("75,425") == 75.425
    assert ebike_float("107,000") == 107.0
    assert ebike_float("1.100") == 1100.0  # qty, not 1.1
    assert ebike_float("1.640.493") == 1640493.0
    assert ebike_float("800") == 800.0
    assert ebike_float("3,18") == 3.18


def test_classify_prefers_ebike_over_ma_ak():
    text = _text("AX00011139")
    fid, score = classify(text, "hashed.pdf")
    assert fid == "ebike_ax_billing_v1"
    assert score >= 0.3
    assert ma_ak_billing_v1.match_score(text, "hashed.pdf") < 0.3
    assert ebike_ax_billing_v1.match_score(text, "hashed.pdf") > ma_ak_billing_v1.match_score(
        text, "hashed.pdf"
    )


def test_ma_ak_fixture_still_classifies_as_ak():
    ak = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "ma_ak_AK00074096_layout.txt"
    )
    text = ak.read_text()
    fid, score = classify(text, "Invoice AK00074096.PDF")
    assert fid == "ma_ak_billing_v1"
    assert score >= 0.3
    assert ebike_ax_billing_v1.match_score(text, "Invoice AK00074096.PDF") < 0.3


def test_all_18_header_lines_currency_and_hard_check():
    ship_pkg = ship_gw = 0.0
    for inv, (nlines, amount, pkg, gw, miss) in GOLD.items():
        res = extract_from_text(_text(inv), source_file=f"{inv}.pdf")
        h, items, meta = res.header, res.items, res.meta
        assert meta.format_id == "ebike_ax_billing_v1"
        assert h.invoice_no == inv
        assert h.invoice_date == "2026-08-27"
        assert h.currency == "EUR"
        assert h.incoterm == "FCA Miskolc"
        assert h.item_line_count == nlines == len(items)
        assert h.amount == amount
        assert meta.labeled_amount == amount
        assert h.total_pkg == pkg
        assert h.gross_weight_kg == gw
        # HUF conversion must not win
        assert h.amount < 100_000
        missing = [it.part_no for it in items if not it.hs_code]
        assert missing == MISSING_HS.get(inv, [])
        assert len(missing) == miss
        hard = hard_check(res.to_dict())
        assert hard["verdict"] == "pass", (inv, hard)
        if miss:
            assert "soft: Commodity Code not printed" in (meta.notes or "")
            assert "HS left empty" in (h.summary_note or "")
            assert "soft: Commodity Code not printed" in (h.summary_note or "")
        else:
            assert "Commodity Code not printed" not in (meta.notes or "")
        ship_pkg += pkg
        ship_gw += gw
    # Per-invoice totals, not a repeated shipment figure.
    assert ship_pkg == 18.0
    assert ship_gw == 2446.0


def test_pricing_unit_and_european_qty():
    res = extract_from_text(_text("AX00011135"))
    # 1.100 PC × 242,13 / 100 PC = 2.663,43
    first = res.items[0]
    assert first.part_no == "EB12.100.015-1CF"
    assert first.qty == 1100.0
    assert first.unit_price == 242.13
    assert first.amount == 2663.43
    assert first.pricing_unit == 100.0
    assert first.hs_code
    assert first.origin
    # semicolon in description must not drop the pricing unit (AX00011148 item 15)
    res = extract_from_text(_text("AX00011148"))
    kit = next(it for it in res.items if it.part_no == "EB13.900.029-VE4")
    assert kit.pricing_unit == 100.0
    assert kit.qty == 120.0
    assert kit.unit_price == 1025.48
    assert kit.amount == 1230.58
    assert "Service kit" in (kit.description or "")


def test_missing_hs_is_printed_omission_not_parser_skip():
    """AX00011144 / 11145 / 11148 item 12 really have no Commodity Code in the text."""
    t44 = _text("AX00011144")
    assert "EB12.100.076-VE4" in t44
    assert "Commodity Code" not in t44
    t48 = _text("AX00011148")
    # other lines on 11148 do print Commodity Code; the service-kit line does not
    assert "EB13.900.025-VE4" in t48
    idx = t48.index("EB13.900.025-VE4")
    nxt = t48.index("EB12.900.019-VE4")
    assert "Commodity Code" not in t48[idx:nxt]


def test_anomalous_line_nw_is_kept_and_noted():
    """AX00011148 prints 8.292,000 KG on one line vs Total Net Weight 33,097 — do not rewrite."""
    res = extract_from_text(_text("AX00011148"))
    kit = next(it for it in res.items if it.part_no == "EB13.900.029-VE4")
    assert kit.net_weight == 8292.0
    assert "line_nw_exceeds_total_nw" in (res.meta.notes or "")
    assert "kept as printed" in (res.header.summary_note or "")
    assert "EB13.900.029-VE4" in (res.header.summary_note or "")
    # 11148 also has a missing HS — both soft warnings share the Summary note
    assert "Commodity Code not printed" in (res.header.summary_note or "")
    assert hard_check(res.to_dict())["verdict"] == "pass"


def test_summary_note_is_excel_comment_on_result(tmp_path):
    """Packages / G.W. cells carry the soft HS + line-NW notes (visible in Result)."""
    from invoice_extractor.export import write_extract, SUMMARY_GW_COL, SUMMARY_COLS

    res = extract_from_text(_text("AX00011148"), source_file="AX00011148.pdf")
    out = tmp_path / "InvoiceExtract_Result.xlsx"
    write_extract(res.to_dict(), out)
    from openpyxl import load_workbook

    wb = load_workbook(out)
    ws = wb["Summary"]
    pkg_col = SUMMARY_COLS.index("Packages") + 1
    gw_col = SUMMARY_COLS.index(SUMMARY_GW_COL) + 1
    note = ws.cell(2, pkg_col).comment
    assert note and "line_nw_exceeds_total_nw" in note.text
    assert "Commodity Code not printed" in note.text
    assert "EB13.900.029-VE4" in note.text
    assert ws.cell(2, gw_col).comment and "kept as printed" in ws.cell(2, gw_col).comment.text
