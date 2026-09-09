# InvoiceExtractor v1 — Overnight REPORT

**Date:** 2026-09-10 (PT / Asia/Taipei)  
**User / org:** Dejureka  
**Auditor bot:** `87eb5fb7-863d-4404-8489-9b16d6c8ef69`（對帳／語意檢查／未命中格式金標可丟給 Auditor；本套件本地只做硬校驗）

## What was built

Portable package at `/workspace/InvoiceExtractor`:

| Path | Role |
|------|------|
| `src/invoice_extractor/schema.py` | header (+ origin/hs) + items + meta；歐式/美式數字、德式/英文日期 |
| `text_layer.py` | wrap vendored `pdf_layout_text`；空文字 → `needs_ocr` |
| `db.py` | SQLite `vendors` / `formats` / `runs`；`--init-db` 種子 |
| `checker.py` | 硬校驗（行數／qty／amount／幣別／單價×量） |
| `rules_engine.py` | classify + apply format |
| `formats/bitzer_v1.py` | BITZER/BHC + **origin DE / HS 84143081** |
| `formats/pt_gloria_v1.py` | PT GmbH／Gloria；50656831 保留重複交貨行 |
| `formats/hangji_v1.py` | 广东恒基 GDHJ |
| `formats/nidec_v1.py` | NIDEC / JCH-TW VKT |
| `formats/hitachi_gls_v1.py` | Hitachi GLS / MEH |
| `formats/highly_v1.py` | 海立 HIGHLY 26020900066 |
| `vendor/pdf_layout_text/` | vendored layout text（PyInstaller / 免外裝） |
| `InvoiceExtractor.spec` + `.github/workflows/build-portable-windows.yml` | Windows portable zip → `portable-latest` release |
| `data/invoice_formats.db` | 種子 DB |
| `tests/` | schema / checker / bitzer(+origin/hs) / PT |
| `reports/round1_pt.md` / `round2_bhc.md` / `round3_all.md` | 驗證表 |
| `out/auditor_batch_summary.md` | 給 Tools→Auditor |

**刻意不做（DESIGN）：** OCR、自動改 code、GUI、LLM 直連。xls 未解析（v1 PDF-only）。

## Round3 — all samples (current)

來源：PT `/workspace/msg_extract/**/*.PDF` + BHC mega `/home/box/Downloads/BHC_invoice_samples_mega/*.pdf`。

| status | PDF | invoice_no | amount | items | format | verdict |
|--------|-----|------------|--------|-------|--------|---------|
| PASS | 50656407.PDF | 50656407 | 10091.68 | 12 | pt_gloria_v1 | pass |
| PASS | 50656462.PDF | 50656462 | 10958.4 | 5 | pt_gloria_v1 | pass |
| PASS | 50656463.PDF | 50656463 | 2506.32 | 1 | pt_gloria_v1 | pass |
| PASS | 50656831.PDF | 50656831 | 114354.38 | 374 | pt_gloria_v1 | pass |
| PASS | 50656853.PDF | 50656853 | 87166.76 | 14 | pt_gloria_v1 | pass |
| PASS | 50661052.PDF | 50661052 | 29587.2 | 1 | pt_gloria_v1 | pass |
| PASS | 50661078.PDF | 50661078 | 5221.44 | 2 | pt_gloria_v1 | pass |
| PASS | 3000214469_…Versanddokument.pdf | 200167553 | 37041.41 | 5 | bitzer_v1 | pass（origin=DE hs=84143081） |
| PASS | GDHJ-250980…台湾博世 12-26.pdf | GDHJ-250980 | 797718.3 | 122 | hangji_v1 | pass |
| PASS | JCH-TW_VKT25097_….pdf | VKT25097 | 13062.96 | 3 | nidec_v1 | pass |
| PASS | JCH-TW_VKT25098_….pdf | VKT25098 | 85846.13 | 5 | nidec_v1 | pass |
| PASS | SD(TW)_…MEH6A036….pdf | MEH6A036 | 631789 | 16 | hitachi_gls_v1 | pass |
| PASS | 台湾博世 26020900066 DOCS.pdf | 26020900066 | 522785.34 | 7 | highly_v1 | pass |

**13/13 hard_check pass.** 詳見 `reports/round3_all.md`、`out/auditor_batch_summary.md`。JSON：`out/*.json`。

### Key fixes

1. **50656831**（原 ~3% conflict）：全局「整行去重」誤刪合法重複交貨行；改為保留全部 material 行，並允許 `F.016…` 料號。raw sum = header 114354.38。
2. **BITZER Auditor 疑點**：補抽 `Country of origin` / `HS-Code` → header + 每列。
3. **BHC NEEDS_GOLD**：四個新 format seed，全部 pass。

## How to run

```bash
# from repo root (vendor on path via pyproject / PYTHONPATH)
pip install -e .
python3 -m invoice_extractor --init-db
python3 -m invoice_extractor path.pdf --out out.json
python3 -m invoice_extractor path.pdf --gold gold.json
pytest -q
```

口語說明：`README.md`（繁中）。

## Portable Windows

- Spec: `InvoiceExtractor.spec`（collect `invoice_extractor` + `pdf_layout_text` + `data/`）
- Workflow: `.github/workflows/build-portable-windows.yml` → artifact + GitHub Release tag **`portable-latest`**
- Entry: `run_cli.py`

## Failures / known gaps

1. ~~50656831 conflict~~ → **fixed in Round3**.
2. ~~非 BITZER BHC mega NEEDS_GOLD~~ → **seeded + pass**.
3. **xls** 仍未做。
4. 部分 PT 單據 pkg/gw 欄位仍可能缺（layout 無清晰合計）；不影響硬校驗。
5. VBA Gloria paste 形狀 ≠ pdftotext layout；PT 以 layout 為準。

## GitHub

- URL: https://github.com/Dejureka/InvoiceExtractor
- Branch `main`；Round3 後 push 觸發 portable Windows workflow / `portable-latest` release。

## Auditor note

Auditor id=`87eb5fb7-863d-4404-8489-9b16d6c8ef69`。本地 CLI `--gold` 只做欄位 diff + 硬校驗；語意對帳交給 Auditor。Batch 表：`out/auditor_batch_summary.md`。
