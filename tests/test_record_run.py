"""CLI writes the runs table only when --record-run is passed."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

REPO_DB = Path(__file__).resolve().parents[1] / "data" / "invoice_formats.db"


def _runs_count(db_path: Path) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0])
    finally:
        conn.close()


def _setup_extract(tmp_path: Path, monkeypatch):
    from invoice_extractor import cli as cli_mod
    import invoice_extractor.pairing as pairing_mod

    sample = {
        "header": {"invoice_no": "X", "amount": 1.0},
        "items": [{"part_no": "P", "qty": 1}],
        "meta": {
            "format_id": "demo",
            "confidence": "rules",
            "source_file": "inv.pdf",
            "pair_status": "僅 INV",
        },
        "_hard": {"verdict": "pass", "issues": []},
    }
    pdf = tmp_path / "inv.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    out = tmp_path / "out.xlsx"
    db = tmp_path / "invoice_formats.db"
    shutil.copy2(REPO_DB, db)
    monkeypatch.setattr(
        pairing_mod, "extract_pair_row", lambda row, format_id=None: dict(sample)
    )
    return cli_mod, pdf, out, db


def test_extract_without_record_run_does_not_write_runs(tmp_path, monkeypatch):
    cli_mod, pdf, out, db = _setup_extract(tmp_path, monkeypatch)
    before = _runs_count(db)
    code = cli_mod.main([str(pdf), "--out", str(out), "--db", str(db)])
    assert code == 0
    assert _runs_count(db) == before


def test_extract_with_record_run_writes_runs(tmp_path, monkeypatch):
    cli_mod, pdf, out, db = _setup_extract(tmp_path, monkeypatch)
    before = _runs_count(db)
    code = cli_mod.main(
        [str(pdf), "--out", str(out), "--db", str(db), "--record-run"]
    )
    assert code == 0
    assert _runs_count(db) == before + 1
