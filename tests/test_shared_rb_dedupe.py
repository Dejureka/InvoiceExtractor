"""Shipment-level shared RB dedupe (user decision 2026-09-29, MA 3rd 008 / 036).

Rule (mode B, default): in an MA shipment (same folder / same BL No.) with
several invoices where an RB key repeats, the shipment's RB-deduped pkg / GW
goes on the first invoice (by invoice number) and every other invoice gets
pkg / GW 0 plus a Summary note; lines untouched. Shipments without a repeated
RB keep each invoice's own printed values. Mode A (zero only the duplicate RB)
stays available via ``mode="duplicate_only"``.
"""

from __future__ import annotations

import copy
from pathlib import Path

import pytest
from openpyxl import load_workbook

from invoice_extractor.export import SUMMARY_SHEET, write_extracts
from invoice_extractor.formats.ma_common import parse_rb_packages, parse_rb_units
from invoice_extractor.pairing import SHARED_RB_MODES, dedupe_shared_packing_units

A, B = "duplicate_only", "shipment_first"

MA3 = Path("/home/box/Downloads/MA-batch-final/MA_3rd data/3rd data")


def _d(inv, units, folder="/x/90-C-26MA-008", bl="COSU6431163410", pkg=None, gw=None, lines=1):
    pkg = float(len(units)) if pkg is None else pkg
    gw = round(sum(units.values()), 3) if gw is None else gw
    return {
        "header": {"invoice_no": inv, "total_pkg": pkg, "gross_weight_kg": gw, "amount": 100.0,
                   "currency": "TWD", "item_line_count": lines, "total_quantity": 1.0, "bl_no": bl,
                   "bl_packages": 26.0, "bl_gross_weight_kg": 1989.837},
        "items": [{"invoice_no": inv, "part_no": "1 234 567 890", "qty": 1.0, "amount": 100.0,
                   "hs_code": "84099910", "origin": "Germany"}],
        "meta": {"source_file": f"{folder}/INVOICE {inv}.PDF", "inv_file": f"{folder}/INVOICE {inv}.PDF",
                 "format_id": "ma_with_period_v1", "confidence": "rules", "packing_units": dict(units),
                 "labeled_amount": 100.0, "labeled_amount_label": "Goods value"},
    }


def test_008_shape_first_invoice_keeps_later_zeroed():
    a = _d("2120394532", {"110936597": 11.604})
    others = {f"1109{i:05d}": 76.0 for i in range(24)}
    others["110999999"] = 154.232  # 24×76 + 154.232 + 11.604 = 1989.836
    b = _d("2120394533", {**others, "110936597": 11.604}, gw=1989.836)
    b_items = copy.deepcopy(b["items"])
    notes = dedupe_shared_packing_units([b, a], mode=A)  # input order must not matter
    assert (a["header"]["total_pkg"], a["header"]["gross_weight_kg"]) == (1.0, 11.604)
    assert not a["header"].get("summary_note")
    assert (b["header"]["total_pkg"], b["header"]["gross_weight_kg"]) == (25.0, 1978.232)
    assert b["items"] == b_items  # line qty / amounts untouched
    assert b["meta"]["packing_units_zeroed"] == {"110936597": 11.604}
    n = b["header"]["summary_note"]
    assert "shared RB 110936597 with 2120394532, zeroed" in n and "printed pkg/GW 26 / 1989.836" in n
    assert n in b["meta"]["notes"] and len(notes) == 1
    total = (a["header"]["total_pkg"] + b["header"]["total_pkg"],
             round(a["header"]["gross_weight_kg"] + b["header"]["gross_weight_kg"], 3))
    assert total == (26.0, 1989.836)
    assert b["meta"]["checker_verdict"] == "pass"


def test_036_shape_three_invoices_only_owner_keeps():
    a = _d("2120422517", {"111292965": 83.5}, folder="/x/036", bl="COSU6438665680")
    b = _d("2120422518", {"111292560": 72.0, "111292965": 83.5, "111299999": 10.0}, folder="/x/036",
           bl="COSU6438665680")
    c = _d("2120422519", {"111300001": 20.0}, folder="/x/036", bl="COSU6438665680")
    dedupe_shared_packing_units([a, b, c], mode=A)
    assert b["header"]["total_pkg"] == 2.0 and b["header"]["gross_weight_kg"] == 82.0
    assert a["header"]["total_pkg"] == 1.0 and not c["header"].get("summary_note")


def test_different_shipments_are_not_deduped():
    a = _d("2120394532", {"110936597": 11.604}, folder="/x/008")
    b = _d("2120394533", {"110936597": 11.604}, folder="/x/009")          # other folder
    c = _d("2120394534", {"110936597": 11.604}, folder="/x/008", bl="COSU0000000001")  # other BL
    for mode in (A, B):
        assert dedupe_shared_packing_units(copy.deepcopy([a, b, c]), mode=mode) == []
    dedupe_shared_packing_units([a, b, c], mode=B)
    assert all(d["header"]["total_pkg"] == 1.0 and not d["header"].get("summary_note") for d in (a, b, c))


def test_totals_not_from_units_are_flagged_not_zeroed():
    a = _d("2120394532", {"110936597": 11.604})
    b = _d("2120394533", {"110936597": 11.604, "110900001": 5.0}, pkg=3.0, gw=30.0)  # e.g. PKL override
    dedupe_shared_packing_units([a, b], mode=A)
    assert (b["header"]["total_pkg"], b["header"]["gross_weight_kg"]) == (3.0, 30.0)
    assert "NOT zeroed" in b["header"]["summary_note"]
    assert {"total_pkg", "gross_weight_kg"} <= set(b["meta"]["needs_gold_fields"])
    assert b["meta"]["checker_verdict"] == "needs_gold"


def test_no_units_no_change():
    a = _d("1", {"1": 1.0}); a["meta"]["packing_units"] = None
    b = _d("2", {"1": 1.0}); b["meta"]["packing_units"] = None
    assert dedupe_shared_packing_units([a, b], mode=A) == []
    assert dedupe_shared_packing_units([a, b], mode=B) == []


def test_parse_rb_units_matches_packages():
    text = (
        "RB 110936597  Corrug. brown box  546/343/295MM  Gross 11.604 KG\n  Net 10.644 KG\n"
        "RB 110936598  Packing Set  Gross 83.500 KG\n"
        "RB 110936597  Corrug. brown box  Gross 11.604 KG\n"
    )
    assert parse_rb_units(text) == {"110936597": 11.604, "110936598": 83.5}
    assert parse_rb_packages(text) == (2.0, 95.104)


def test_summary_note_written_as_excel_note(tmp_path):
    a = _d("2120394532", {"110936597": 11.604})
    b = _d("2120394533", {"110936597": 11.604, "110900001": 5.0})
    dedupe_shared_packing_units([a, b], mode=A)
    out = write_extracts([a, b], tmp_path / "r.xlsx")
    ws = load_workbook(out)[SUMMARY_SHEET]
    hdr = [c.value for c in ws[1]]
    assert hdr[-3:] == ["BL No.", "BL Packages", "BL G.W. (kgs)"]  # layout unchanged
    row3 = {h: ws.cell(3, i + 1) for i, h in enumerate(hdr)}
    assert row3["Packages"].value == 1.0 and row3["G.W. (kgs)-Air DIM. (CBM)-Sea"].value == 5.0
    assert "shared RB 110936597 with 2120394532" in row3["Packages"].comment.text
    assert ws.cell(2, 2).comment is None


# ------------------------------------------------ mode B (shipment total on first)

def test_mode_b_008_shape_whole_shipment_on_first_invoice():
    a = _d("2120394532", {"110936597": 11.604})
    others = {f"1109{i:05d}": 76.0 for i in range(24)}
    others["110999999"] = 154.232
    b = _d("2120394533", {**others, "110936597": 11.604}, gw=1989.836)
    items = copy.deepcopy([a["items"], b["items"]])
    dedupe_shared_packing_units([b, a], mode=B)
    assert (a["header"]["total_pkg"], a["header"]["gross_weight_kg"]) == (26.0, 1989.836)
    assert (b["header"]["total_pkg"], b["header"]["gross_weight_kg"]) == (0.0, 0.0)
    assert [a["items"], b["items"]] == items
    assert a["header"]["summary_note"] == (
        "shipment pkg/GW (deduped) 26 / 1989.836 on this first invoice (2 invoices, "
        "shared RB 110936597); printed pkg/GW 1 / 11.604"
    )
    assert b["header"]["summary_note"] == "shipment pkg/GW (deduped) on 2120394532; printed pkg/GW 26 / 1989.836"
    assert a["meta"]["shipment_packing"]["shared_rb"] == ["110936597"]
    assert a["meta"]["checker_verdict"] == b["meta"]["checker_verdict"] == "pass"


def test_mode_b_036_shape_all_later_invoices_zeroed():
    kw = dict(folder="/x/036", bl="COSU6438665680")
    a = _d("2120422517", {"111292965": 83.5}, **kw)
    b = _d("2120422518", {"111292560": 72.0, "111292965": 83.5, "111299999": 10.0}, **kw)
    c = _d("2120422519", {"111300001": 20.0}, **kw)
    dedupe_shared_packing_units([c, b, a], mode=B)
    assert (a["header"]["total_pkg"], a["header"]["gross_weight_kg"]) == (4.0, 185.5)
    assert (b["header"]["total_pkg"], c["header"]["total_pkg"]) == (0.0, 0.0)
    assert c["header"]["gross_weight_kg"] == 0.0 and c["header"]["summary_note"]


def test_mode_b_bad_totals_flag_whole_shipment():
    a = _d("1", {"k1": 1.0})
    b = _d("2", {"k1": 1.0, "k2": 2.0}, pkg=5.0, gw=50.0)
    dedupe_shared_packing_units([a, b], mode=B)
    assert (a["header"]["total_pkg"], b["header"]["total_pkg"]) == (1.0, 5.0)
    assert all("NOT zeroed" in d["header"]["summary_note"] for d in (a, b))


def test_default_mode_is_b_shipment_first():
    from invoice_extractor import pairing

    assert pairing.SHARED_RB_MODE == B
    a = _d("2120394532", {"110936597": 11.604})
    b = _d("2120394533", {"110936597": 11.604, "110900001": 5.0})
    dedupe_shared_packing_units([a, b])  # no mode → default
    assert (a["header"]["total_pkg"], b["header"]["total_pkg"]) == (2.0, 0.0)


def test_unknown_mode_rejected():
    assert SHARED_RB_MODES == (A, B)
    with pytest.raises(ValueError):
        dedupe_shared_packing_units([], mode="C")


# ------------------------------------------------ real samples (optional)

@pytest.mark.parametrize(
    "mode,folder,expect,per_inv,noted",
    [
        (A, "RBDEsea/90-C-26MA-008", (26.0, 1989.836),
         {"2120394532": (1.0, 11.604), "2120394533": (25.0, 1978.232)}, ["2120394533"]),
        (A, "RBDEsea/90-C-26MA-036", (32.0, 2801.031),
         {"2120422517": (1.0, 83.5), "2120422518": (2.0, 229.5), "2120422519": (29.0, 2488.031)},
         ["2120422518"]),
        (B, "RBDEsea/90-C-26MA-008", (26.0, 1989.836),
         {"2120394532": (26.0, 1989.836), "2120394533": (0.0, 0.0)}, ["2120394532", "2120394533"]),
        (B, "RBDEsea/90-C-26MA-036", (32.0, 2801.031),
         {"2120422517": (32.0, 2801.031), "2120422518": (0.0, 0.0), "2120422519": (0.0, 0.0)},
         ["2120422517", "2120422518", "2120422519"]),
    ],
)
def test_ma3_shared_rb_folders(mode, folder, expect, per_inv, noted):
    from invoice_extractor.pairing import auto_pair, extract_pair_row

    d = MA3 / folder
    if not d.is_dir():
        pytest.skip(f"missing {d}")
    datas = []
    for row in auto_pair(sorted(d.iterdir())):
        if row.inv_path:
            x = extract_pair_row(row)
            x.pop("_hard"); x.pop("_pair_status", None); x.pop("_pair_id", None)
            datas.append(x)
    dedupe_shared_packing_units(datas, mode=mode)
    got = {x["header"]["invoice_no"]: (x["header"]["total_pkg"], x["header"]["gross_weight_kg"]) for x in datas}
    assert got == per_inv
    tot = (sum(v[0] for v in got.values()), round(sum(v[1] for v in got.values()), 3))
    assert tot == expect
    assert sorted(x["header"]["invoice_no"] for x in datas if x["header"].get("summary_note")) == noted
    assert all(x["meta"]["checker_verdict"] == "pass" for x in datas)


def test_mode_b_shipment_without_repeated_rb_keeps_printed_values():
    a = _d("2120419937", {"110000001": 10.0, "110000002": 20.0}, folder="/x/007", bl="COSU6437826540")
    b = _d("2120419938", {"110000003": 5.0}, folder="/x/007", bl="COSU6437826540")
    assert dedupe_shared_packing_units([a, b], mode=B) == []
    assert (a["header"]["total_pkg"], a["header"]["gross_weight_kg"]) == (2.0, 30.0)
    assert (b["header"]["total_pkg"], b["header"]["gross_weight_kg"]) == (1.0, 5.0)
    assert not a["header"].get("summary_note") and not b["header"].get("summary_note")
