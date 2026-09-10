# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path as _P

from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules("invoice_extractor") + collect_submodules("pdf_layout_text")
hidden += ["pdfminer", "pdfminer.high_level"]
# Excel export
hidden += collect_submodules("openpyxl") + collect_submodules("et_xmlfile")
# Self-contained text fallback (when bundled poppler missing)
try:
    hidden += collect_submodules("pymupdf")
except Exception:
    pass
hidden += ["pymupdf", "fitz"]
# Optional drag-drop (best-effort; Browse works without it)
hidden += ["tkinterdnd2"]

# Bundled poppler (downloaded in CI into vendor/poppler)
_poppler_bins = []
for _cand in [
    _P("vendor/poppler/Library/bin"),
    _P("vendor/poppler/bin"),
    _P("poppler/bin"),
]:
    if _cand.is_dir():
        for _f in _cand.iterdir():
            if _f.suffix.lower() in {".exe", ".dll"} or _f.name == "pdftotext":
                _poppler_bins.append((str(_f), "poppler/bin"))
        break

a = Analysis(
    ["run_gui.py"],
    pathex=["src", "vendor"],
    binaries=_poppler_bins,
    datas=[("data", "data")],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="InvoiceExtractor", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True,
    # windowed: double-click opens GUI without console flash; CLI args still work
    console=False,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, upx_exclude=[], name="InvoiceExtractor")
