"""Auto-open of InvoiceExtract_Result.xlsx after a successful GUI Extract."""

from __future__ import annotations

import inspect
import os
import subprocess
import sys
from pathlib import Path

import pytest

import invoice_extractor.gui as gui
from invoice_extractor.pairing import STATUS_INV_ONLY, PairRow


def _sample(row, format_id=None):
    return {
        "header": {"invoice_no": "X1", "amount": 1.0},
        "items": [{"part_no": "P", "qty": 1}],
        "meta": {
            "format_id": "demo",
            "confidence": "rules",
            "source_file": str(row.inv_path),
            "pair_status": STATUS_INV_ONLY,
        },
        "_hard": {"verdict": "pass", "issues": []},
    }


@pytest.fixture
def opener(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(gui, "open_path", lambda p: calls.append(str(p)))
    return calls


def _rows(tmp_path: Path) -> list[PairRow]:
    pdf = tmp_path / "inv.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    return [PairRow(pair_id="P1", inv_path=pdf, status=STATUS_INV_ONLY)]


def test_opens_result_after_successful_write(tmp_path, monkeypatch, opener):
    monkeypatch.setattr(gui, "extract_pair_row", _sample)
    out = tmp_path / "InvoiceExtract_Result.xlsx"
    result = gui._extract_pairs(_rows(tmp_path), out)
    assert out.is_file()
    logs: list[str] = []
    assert gui._auto_open_result(result, logs.append) is True
    assert opener == [str(out)]
    assert any("Opened result" in m for m in logs)


def test_default_result_path_is_opened(tmp_path, monkeypatch, opener):
    import invoice_extractor.export as export_mod

    dest = tmp_path / "InvoiceExtract_Result.xlsx"
    monkeypatch.setattr(export_mod, "default_result_path", lambda root=None: dest)
    monkeypatch.setattr(gui, "extract_pair_row", _sample)
    result = gui._extract_pairs(_rows(tmp_path), None)
    assert Path(result["written"]) == dest
    gui._auto_open_result(result, lambda m: None)
    assert opener == [str(dest)]


def test_not_opened_when_write_fails(tmp_path, monkeypatch, opener):
    """Locked workbook: save raises -> GUI fail() path; nothing is opened."""
    import invoice_extractor.export as export_mod

    def locked(*a, **k):
        raise PermissionError("[Errno 13] Permission denied: 'InvoiceExtract_Result.xlsx'")

    monkeypatch.setattr(gui, "extract_pair_row", _sample)
    monkeypatch.setattr(export_mod, "write_extracts", locked)
    with pytest.raises(PermissionError):
        result = gui._extract_pairs(_rows(tmp_path), tmp_path / "r.xlsx")
        gui._auto_open_result(result, lambda m: None)
    assert opener == []


def test_not_opened_when_nothing_written(tmp_path, monkeypatch, opener):
    def boom(row, format_id=None):
        raise RuntimeError("no format")

    monkeypatch.setattr(gui, "extract_pair_row", boom)
    out = tmp_path / "r.xlsx"
    result = gui._extract_pairs(_rows(tmp_path), out)
    assert result["written"] is None and not out.exists()
    assert gui._auto_open_result(result, lambda m: None) is False
    assert opener == []


def test_not_opened_for_json_or_missing_file(tmp_path, opener):
    j = tmp_path / "r.json"
    j.write_text("{}", encoding="utf-8")
    assert gui._auto_open_result({"written": str(j)}, lambda m: None) is False
    missing = tmp_path / "gone.xlsx"
    assert gui._auto_open_result({"written": str(missing)}, lambda m: None) is False
    assert opener == []


def test_open_failure_is_logged_not_raised(tmp_path, monkeypatch):
    out = tmp_path / "InvoiceExtract_Result.xlsx"
    out.write_bytes(b"x")

    def bad(p):
        raise OSError("no association")

    monkeypatch.setattr(gui, "open_path", bad)
    logs: list[str] = []
    assert gui._auto_open_result({"written": str(out)}, logs.append) is False
    assert logs == ["(open result failed: no association)"]


def test_open_path_windows_uses_startfile(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(os, "startfile", lambda p: calls.append(p), raising=False)
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: pytest.fail("Popen used"))
    gui.open_path(tmp_path / "a.xlsx")
    assert calls == [str(tmp_path / "a.xlsx")]


@pytest.mark.parametrize("plat,cmd", [("darwin", "open"), ("linux", "xdg-open")])
def test_open_path_mac_linux_use_popen(monkeypatch, tmp_path, plat, cmd):
    if hasattr(os, "startfile"):
        monkeypatch.delattr(os, "startfile")
    monkeypatch.setattr(sys, "platform", plat)
    calls = []
    monkeypatch.setattr(subprocess, "Popen", lambda args, **k: calls.append(args))
    gui.open_path(tmp_path / "a.xlsx")
    assert calls == [[cmd, str(tmp_path / "a.xlsx")]]


def test_gui_wires_helper_into_extract_and_ocr():
    src = inspect.getsource(gui.run_gui)
    assert "_auto_open_result(result, self._log)" in src
    assert "open_path(out_dir)" in src
    assert "os.startfile" not in src
