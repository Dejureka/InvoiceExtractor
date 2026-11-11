"""GUI smoke tests — no display required."""

from __future__ import annotations

import importlib
import types
from pathlib import Path


def test_gui_module_imports():
    mod = importlib.import_module("invoice_extractor.gui")
    assert hasattr(mod, "run_gui")
    assert hasattr(mod, "_extract_one")
    assert hasattr(mod, "_extract_many")
    assert hasattr(mod, "_parse_dnd_paths")


def test_parse_dnd_paths_braces():
    from invoice_extractor.gui import _parse_dnd_paths

    assert _parse_dnd_paths(r"C:\a.pdf") == [r"C:\a.pdf"]
    assert _parse_dnd_paths(r"{C:\My Docs\inv.pdf}") == [r"C:\My Docs\inv.pdf"]
    parts = _parse_dnd_paths(r"{C:\a b.pdf} C:\c.pdf")
    assert parts == [r"C:\a b.pdf", r"C:\c.pdf"]


def test_cli_version_no_display():
    """CLI --version works without a display / GUI."""
    from invoice_extractor.cli import main

    try:
        code = main(["--version"])
    except SystemExit as e:
        assert e.code in (0, None)
        return
    assert code in (0, None)


def test_cli_extract_with_args_no_gui(tmp_path: Path, monkeypatch):
    """With PDF args, CLI extract path runs (no window)."""
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

    monkeypatch.setattr(
        pairing_mod, "extract_pair_row", lambda row, format_id=None: dict(sample)
    )

    code = cli_mod.main([str(pdf), "--out", str(out)])
    assert code == 0
    assert out.is_file()


def test_cli_multi_pdfs_one_workbook(tmp_path: Path, monkeypatch):
    from invoice_extractor import cli as cli_mod
    import invoice_extractor.pairing as pairing_mod
    from openpyxl import load_workbook
    from invoice_extractor.export import SUMMARY_SHEET

    def fake_pair_row(row, format_id=None):
        invoice_no = (row.inv_path or row.pkl_path).stem.upper()
        return {
            "header": {
                "invoice_no": invoice_no,
                "amount": 10.0,
                "currency": "USD",
                "item_line_count": 1,
                "total_quantity": 1.0,
            },
            "items": [
                {
                    "invoice_no": invoice_no,
                    "part_no": "P",
                    "qty": 1,
                    "amount": 10.0,
                }
            ],
            "meta": {
                "format_id": "demo",
                "confidence": "rules",
                "source_file": f"{invoice_no}.pdf",
                "pair_status": "僅 INV",
            },
            "_hard": {"verdict": "pass", "issues": []},
        }

    pdfs = []
    for name in ("a.pdf", "b.pdf"):
        p = tmp_path / name
        p.write_bytes(b"%PDF")
        pdfs.append(p)
    out = tmp_path / "batch.xlsx"

    monkeypatch.setattr(pairing_mod, "extract_pair_row", fake_pair_row)

    code = cli_mod.main([str(pdfs[0]), str(pdfs[1]), "--out", str(out)])
    assert code == 0
    assert out.is_file()
    wb = load_workbook(out)
    assert wb[SUMMARY_SHEET].max_row == 3


def test_extract_many_partial_failure(tmp_path: Path, monkeypatch):
    from invoice_extractor import gui as gui_mod
    import invoice_extractor.pairing as pairing_mod
    from openpyxl import load_workbook
    from invoice_extractor.export import META_SHEET, SUMMARY_SHEET

    good = tmp_path / "good.pdf"
    bad = tmp_path / "bad.pdf"
    good.write_bytes(b"%PDF")
    bad.write_bytes(b"%PDF")
    out = tmp_path / "partial.xlsx"

    def fake_pair_row(row, format_id=None):
        pdf = row.inv_path or row.pkl_path
        if pdf and pdf.name == "bad.pdf":
            raise RuntimeError("parse failed")
        return {
            "header": {
                "invoice_no": "G1",
                "amount": 1.0,
                "currency": "USD",
                "item_line_count": 0,
                "total_quantity": 0,
            },
            "items": [],
            "meta": {
                "source_file": str(pdf),
                "format_id": "demo",
                "confidence": "rules",
                "pair_status": "僅 INV",
            },
            "_hard": {"verdict": "pass", "issues": []},
            "_pair_status": "僅 INV",
        }

    monkeypatch.setattr(pairing_mod, "extract_pair_row", fake_pair_row)
    monkeypatch.setattr(gui_mod, "extract_pair_row", fake_pair_row)
    result = gui_mod._extract_many([good, bad], out)
    assert result["successes"] == 1
    assert len(result["failures"]) == 1
    assert Path(result["written"]).is_file()
    wb = load_workbook(result["written"])
    assert wb[SUMMARY_SHEET].max_row == 2
    assert wb[META_SHEET].max_row == 3


def _load_run_gui():
    import importlib.util
    import sys

    root = Path(__file__).resolve().parents[1]
    path = root / "run_gui.py"
    spec = importlib.util.spec_from_file_location("run_gui_entry", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["run_gui_entry"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_run_gui_routes_cli_when_args(monkeypatch):
    """run_gui.main with args delegates to CLI, does not open GUI."""
    rg = _load_run_gui()

    called: dict = {}

    def fake_cli(argv):
        called["argv"] = list(argv)
        return 7

    fake_mod = types.ModuleType("invoice_extractor.cli")
    fake_mod.main = fake_cli
    monkeypatch.setitem(__import__("sys").modules, "invoice_extractor.cli", fake_mod)

    def boom():
        raise AssertionError("GUI should not open when args present")

    fake_gui = types.ModuleType("invoice_extractor.gui")
    fake_gui.run_gui = boom
    monkeypatch.setitem(__import__("sys").modules, "invoice_extractor.gui", fake_gui)

    monkeypatch.setattr(
        __import__("sys"), "argv", ["run_gui.py", "doc.pdf", "--out", "o.xlsx"]
    )
    assert rg.main() == 7
    assert called["argv"] == ["doc.pdf", "--out", "o.xlsx"]


def test_run_gui_routes_gui_when_no_args(monkeypatch):
    """run_gui.main with no args opens GUI (mocked)."""
    rg = _load_run_gui()

    opened = {"ok": False}

    def fake_run_gui():
        opened["ok"] = True

    fake_gui = types.ModuleType("invoice_extractor.gui")
    fake_gui.run_gui = fake_run_gui
    monkeypatch.setitem(__import__("sys").modules, "invoice_extractor.gui", fake_gui)
    monkeypatch.setattr(__import__("sys"), "argv", ["run_gui.py"])
    assert rg.main() == 0
    assert opened["ok"] is True


def test_parse_dnd_paths_literal_brace_in_hash():
    """Outlook-style stems like …EA}1.pdf must not split on the closing brace."""
    from invoice_extractor.gui import _parse_dnd_paths

    hashed = r"C:\inbox\75ed0f40E47A859D-C95D-4C83-A55A-8E43A0FB9571}1.pdf"
    assert _parse_dnd_paths(hashed) == [hashed]
    # mixed: braced path with spaces, then an unquoted hash containing }
    mixed = r"{C:\My Docs\inv.pdf} " + hashed
    assert _parse_dnd_paths(mixed) == [r"C:\My Docs\inv.pdf", hashed]
    two_hash = hashed + " " + hashed.replace("75ed", "6a8e")
    assert len(_parse_dnd_paths(two_hash)) == 2
    assert all(p.endswith("}1.pdf") for p in _parse_dnd_paths(two_hash))


def _tcl_list(*paths: str) -> str:
    """Serialize paths the way tkdnd puts them in event.data (Tcl list)."""
    import tkinter

    tcl = tkinter.Tcl()
    for i, path in enumerate(paths):
        tcl.call("set", f"::p{i}", path)
    return tcl.eval("list " + " ".join(f"$::p{i}" for i in range(len(paths))))


def test_parse_dnd_paths_authentic_tcl_payloads(tmp_path: Path):
    """Windows tkdnd payloads come from Tcl list quoting — use splitlist."""
    from invoice_extractor.gui import _parse_dnd_paths, _parse_dnd_paths_fallback

    spaced = r"C:\My Docs\inv.pdf"
    hashed = (
        r"C:\Users\YAP1TP\Desktop\My Invoices"
        r"\75ed0f4055F7F11D-E463-4AFA-A5B1-E032D82D4064}1.pdf"
    )
    upper = r"C:\WORK\INVOICE.PDF"
    folder = r"C:\Users\YAP1TP\Desktop\My Invoices"

    # Brace-wrapped path with spaces
    raw_space = _tcl_list(spaced)
    assert raw_space.startswith("{") and " " in raw_space
    assert _parse_dnd_paths(raw_space) == [os_norm := __import__("os").path.normpath(spaced)]

    # Backslash-escaped } (and doubled backslashes) — the eBike Outlook hash
    raw_hash = _tcl_list(hashed)
    assert r"\}" in raw_hash
    got = _parse_dnd_paths(raw_hash)
    assert got == [__import__("os").path.normpath(hashed)]
    # The previous custom parser kept the escape, so the path did not exist
    old = _parse_dnd_paths_fallback(raw_hash)
    assert any("\\}" in p for p in old), old
    assert old != got

    # Uppercase .PDF
    raw_upper = _tcl_list(upper)
    assert _parse_dnd_paths(raw_upper) == [__import__("os").path.normpath(upper)]

    # Multiple files
    raw_multi = _tcl_list(spaced, hashed)
    assert _parse_dnd_paths(raw_multi) == [
        __import__("os").path.normpath(spaced),
        __import__("os").path.normpath(hashed),
    ]

    # Folder
    raw_folder = _tcl_list(folder)
    assert _parse_dnd_paths(raw_folder) == [__import__("os").path.normpath(folder)]

    # Forward-slash Windows path with escaped }
    fwd = "C:/Users/YAP1TP/Desktop/InvoiceExtractor/75ed0f4055F7F11D-E463-4AFA-A5B1-E032D82D4064}1.pdf"
    raw_fwd = _tcl_list(fwd)
    assert r"\}" in raw_fwd
    assert _parse_dnd_paths(raw_fwd) == [__import__("os").path.normpath(fwd)]


def test_expand_dnd_uppercase_pdf_and_folder(tmp_path: Path):
    """Extension match is case-insensitive; a dropped folder is expanded."""
    from invoice_extractor.gui import _parse_dnd_paths, _expand_pdf_inputs

    docs = tmp_path / "My Invoices"
    docs.mkdir()
    pdf = docs / "75ed0f4055F7F11D-E463-4AFA-A5B1-E032D82D4064}1.pdf"
    pdf.write_bytes(b"%PDF-1.4 test")
    upper = docs / "INVOICE.PDF"
    upper.write_bytes(b"%PDF-1.4 test")
    xlsx = docs / "pack.xlsx"
    xlsx.write_bytes(b"PK\x03\x04")

    # Drop the uppercase file
    raw = _tcl_list(str(upper))
    files = _expand_pdf_inputs(_parse_dnd_paths(raw))
    assert [p.resolve() for p in files] == [upper.resolve()]

    # Drop the folder
    raw_dir = _tcl_list(str(docs))
    files = sorted(_expand_pdf_inputs(_parse_dnd_paths(raw_dir)), key=lambda p: p.name.lower())
    names = {p.name for p in files}
    assert "INVOICE.PDF" in names
    assert "75ed0f4055F7F11D-E463-4AFA-A5B1-E032D82D4064}1.pdf" in names
    assert "pack.xlsx" in names


def test_on_drop_logs_raw_payload_when_empty(tmp_path: Path, monkeypatch):
    """Failed drops write event.data (repr, ≤300 chars) to Summary and a log file."""
    from invoice_extractor import gui as gui_mod
    from invoice_extractor import export as export_mod

    monkeypatch.setattr(export_mod, "tool_root", lambda: tmp_path)
    log = tmp_path / "InvoiceExtractor_drop.log"
    if log.exists():
        log.unlink()

    raw = _tcl_list(
        r"C:\Users\YAP1TP\Desktop\My Invoices"
        r"\75ed0f4055F7F11D-E463-4AFA-A5B1-E032D82D4064}1.pdf"
    )
    # Path is on a fake Windows drive, so collect_pdfs finds nothing
    parts = gui_mod._parse_dnd_paths(raw)
    assert parts and parts[0].endswith("}1.pdf")
    path = gui_mod._drop_debug_log(raw, parts, errors=["Path not found: " + parts[0]])
    assert path == log
    text = log.read_text(encoding="utf-8")
    assert "Drop ignored: no PDF/Excel inputs found" in text
    assert "event.data=" in text
    assert "\\}" in text or "}1.pdf" in text
    assert len(text.split("event.data=", 1)[1].splitlines()[0]) <= 300 + 20
