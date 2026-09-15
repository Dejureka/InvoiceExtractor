"""INV+PKL pairing helpers (BHC-first) + merge overlay."""

from __future__ import annotations

from pathlib import Path

from invoice_extractor.pairing import (
    STATUS_BL_ONLY,
    STATUS_INV_ONLY,
    STATUS_INV_PKL,
    STATUS_PKL_ONLY,
    auto_pair,
    classify_role,
    merge_bl_onto_inv,
    merge_pkl_onto_inv,
    pairing_keys_from_path,
    parse_packing_pkg_gw,
)
from invoice_extractor.schema import ExtractResult, Header, Item, Meta


def test_classify_bhc_inv_pkl_filename(tmp_path: Path):
    inv = tmp_path / "TA2608B2-3253_INV_9027451705.PDF"
    pkl = tmp_path / "TA2608B2-3253_PKL_9027451705.PDF"
    inv.write_bytes(b"%PDF")
    pkl.write_bytes(b"%PDF")
    assert classify_role(inv, filename_only=True).role == "inv"
    assert classify_role(pkl, filename_only=True).role == "pkl"


def test_auto_pair_same_folder_bhc(tmp_path: Path):
    inv = tmp_path / "TA2608B2-3257_INV_9027451746.PDF"
    pkl = tmp_path / "TA2608B2-3257_PKL_9027451746.PDF"
    inv.write_bytes(b"%PDF")
    pkl.write_bytes(b"%PDF")
    rows = auto_pair([inv, pkl])
    assert len(rows) == 1
    assert rows[0].status == STATUS_INV_PKL
    assert rows[0].inv_path == inv
    assert rows[0].pkl_path == pkl


def test_auto_pair_two_segment_ma_names(tmp_path: Path):
    """Same folder + shared invoice no in two-segment stems."""
    inv = tmp_path / "0020029837_2000262902_RBTW_INV.PDF"
    pkl = tmp_path / "0020029837_2000262902_RBTW_PKL.PDF"
    inv.write_bytes(b"%PDF")
    pkl.write_bytes(b"%PDF")
    keys_i = pairing_keys_from_path(inv)
    keys_p = pairing_keys_from_path(pkl)
    assert "inv:2000262902" in keys_i
    assert "inv:2000262902" in keys_p
    rows = auto_pair([inv, pkl])
    assert len(rows) == 1
    assert rows[0].status == STATUS_INV_PKL


def test_auto_pair_inv_only(tmp_path: Path):
    inv = tmp_path / "TA2608B2-3253_INV_9027451705.PDF"
    inv.write_bytes(b"%PDF")
    rows = auto_pair([inv])
    assert len(rows) == 1
    assert rows[0].status == STATUS_INV_ONLY
    assert rows[0].pkl_path is None


def test_auto_pair_pkl_only(tmp_path: Path):
    pkl = tmp_path / "batch_PKL_9027451705.PDF"
    pkl.write_bytes(b"%PDF")
    rows = auto_pair([pkl])
    assert len(rows) == 1
    assert rows[0].status == STATUS_PKL_ONLY


def test_ma_combined_filename_not_forced_split(tmp_path: Path):
    """MA-style single PDF (no INV/PKL tag) stays one extract unit."""
    pdf = tmp_path / "0020029837_2000262902_RBTW_20260102.PDF"
    pdf.write_bytes(b"%PDF")
    role = classify_role(pdf, filename_only=True)
    assert role.role in ("combined", "unknown")
    rows = auto_pair([pdf])
    assert len(rows) == 1
    assert rows[0].inv_path == pdf
    assert rows[0].pkl_path is None


def test_merge_pkl_supplies_pkg_gw():
    inv = ExtractResult(
        header=Header(
            invoice_no="9027451705",
            amount=100.0,
            currency="USD",
            total_pkg=None,
            gross_weight_kg=None,
        ),
        items=[Item(invoice_no="9027451705", part_no="A", qty=1, amount=100.0)],
        meta=Meta(source_file="inv.pdf", format_id="bhc_my_hub_v1", confidence="rules"),
    )
    pkl_text = """
PACKING LIST
RB 200317606     Packing Set 1200X800X1000      Gross       541.000    KG
RB 200317608     Packing Set 1200X800X1000      Gross       100.000    KG
"""
    merged = merge_pkl_onto_inv(
        inv, pkl_text=pkl_text, pkl_path="x_PKL.pdf", inv_path="x_INV.pdf"
    )
    assert merged.header.total_pkg == 2.0
    assert merged.header.gross_weight_kg == 641.0
    assert merged.meta.source == "split"
    assert merged.meta.pkl_used is True
    assert merged.meta.pair_status == STATUS_INV_PKL
    assert len(merged.items) == 1


def test_parse_packing_bitzer_gesamtgewicht():
    text = "Ladeliste ... Gesamtgewicht 7 6.052,400 KG ..."
    pkg, gw = parse_packing_pkg_gw(text)
    assert pkg == 7.0
    assert gw == 6052.4



def test_combined_annotate_meta():
    """合訂本 single-file path marks source=combined."""
    from invoice_extractor.pairing import annotate_combined_meta

    inv = ExtractResult(
        header=Header(invoice_no="200167553", total_pkg=7, gross_weight_kg=6052.4),
        items=[],
        meta=Meta(source_file="bitzer.pdf", format_id="bitzer_v1", confidence="rules"),
    )
    out = annotate_combined_meta(inv, "bitzer.pdf")
    assert out.meta.source == "combined"
    assert out.meta.pkl_used is True
    assert out.meta.pair_status == STATUS_INV_PKL


def test_bitzer_fixture_still_extracts_combined():
    """Combined PDF regression: BITZER fixture text → packages/GW present."""
    from invoice_extractor.formats import bitzer_v1

    root = Path(__file__).resolve().parents[1]
    fixture = root / "fixtures" / "bitzer_3000214469.txt"
    text = fixture.read_text(encoding="utf-8", errors="replace")
    result = bitzer_v1.extract_from_text(text, source_file="bitzer.pdf", text_backend="fixture")
    assert result.header.invoice_no
    assert result.header.total_pkg is not None
    assert result.header.gross_weight_kg is not None
    assert result.items


def test_classify_bl_filename(tmp_path: Path):
    bl = tmp_path / "到貨 448.pdf"
    bl.write_bytes(b"%PDF")
    assert classify_role(bl, filename_only=True).role == "bl"


def test_auto_pair_same_folder_inv_bl(tmp_path: Path):
    inv = tmp_path / "TA2608B2-3253_INV_9027451705.PDF"
    bl = tmp_path / "到貨 448.pdf"
    inv.write_bytes(b"%PDF")
    bl.write_bytes(b"%PDF")
    rows = auto_pair([inv, bl])
    assert len(rows) == 1
    assert rows[0].inv_path == inv
    assert rows[0].bl_path == bl
    assert rows[0].status == STATUS_INV_ONLY


def test_auto_pair_bl_only(tmp_path: Path):
    bl = tmp_path / "到貨通知 - NGOA23259.pdf"
    bl.write_bytes(b"%PDF")
    rows = auto_pair([bl])
    assert len(rows) == 1
    assert rows[0].status == STATUS_BL_ONLY
    assert rows[0].bl_path == bl


def test_merge_bl_does_not_overwrite_inv_pkg_gw():
    inv = ExtractResult(
        header=Header(invoice_no="X", total_pkg=10.0, gross_weight_kg=100.0),
        items=[],
        meta=Meta(source_file="inv.pdf"),
    )
    out = merge_bl_onto_inv(
        inv,
        bl_header={"bl_no": "WEB1", "packages": 99.0, "gross_weight_kg": 17095.0},
        bl_path="到貨.pdf",
        bl_format_id="ceva_pyramid_arrival_v1",
    )
    assert out.header.total_pkg == 10.0
    assert out.header.gross_weight_kg == 100.0
    assert out.header.bl_no == "WEB1"
    assert out.header.bl_packages == 99.0
    assert out.header.bl_gross_weight_kg == 17095.0
    assert out.meta.bl_used is True



def test_auto_pair_same_folder_multi_inv_one_bl(tmp_path: Path):
    """N INV + 1 BL in same folder: each INV row carries the shared BL path."""
    inv1 = tmp_path / "0020032925_2000270044_RBTW.PDF"
    inv2 = tmp_path / "0020032925_2000270045_RBTW.PDF"
    bl = tmp_path / "到貨通知 HBL005135.pdf"
    for p in (inv1, inv2, bl):
        p.write_bytes(b"%PDF")
    rows = auto_pair([inv1, inv2, bl])
    assert len(rows) == 2
    assert all(r.bl_path == bl for r in rows)
    assert all(r.inv_path in (inv1, inv2) for r in rows)
    assert {r.inv_path for r in rows} == {inv1, inv2}
