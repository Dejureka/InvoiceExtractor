# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hidden = collect_submodules('invoice_extractor') + collect_submodules('pdf_layout_text')
hidden += ['pdfminer', 'pdfminer.high_level']
# Excel export
hidden += collect_submodules('openpyxl') + collect_submodules('et_xmlfile')

a = Analysis(
    ['run_cli.py'],
    pathex=['src', 'vendor'],
    binaries=[],
    datas=[('data', 'data')],
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
    name='InvoiceExtractor', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, console=True,
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, upx_exclude=[], name='InvoiceExtractor')
