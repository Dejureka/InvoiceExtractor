# InvoiceExtractor v1 — Overnight REPORT

**Date:** 2026-09-10 (PT / Asia/Taipei)  
**User / org:** Dejureka  
**Auditor bot:** `87eb5fb7-863d-4404-8489-9b16d6c8ef69`（對帳／語意檢查／未命中格式金標可丟給 Auditor；本套件本地只做硬校驗）

## What was built

Portable package at `/workspace/InvoiceExtractor`:

| Path | Role |
|------|------|
| `src/invoice_extractor/schema.py` | header + items + meta；歐式/美式數字、德式日期 |
| `text_layer.py` | wrap `pdf_layout_text`；空文字 → `needs_ocr` |
| `db.py` | SQLite `vendors` / `formats` / `runs`；`--init-db` 種子 |
| `checker.py` | 硬校驗（行數／qty／amount／幣別／單價×量） |
| `rules_engine.py` | classify + apply format |
| `formats/bitzer_v1.py` | BITZER/BHC，自 BHC_HeaderExtract 移植 |
| `formats/pt_gloria_v1.py` | PT GmbH／Gloria，**pdftotext -layout 真輸出訓練** |
| `gold_stub.py` | needs_gold placeholder；`--gold` 離線比對 |
| `cli.py` / `__main__.py` | CLI |
| `data/invoice_formats.db` | 種子 DB（BITZER v1 + PT Gloria v1） |
| `tests/` | schema / checker / bitzer header / PT invoice_no |
| `reports/round1_pt.md` / `round2_bhc.md` | 驗證表 |

**刻意不做（DESIGN）：** OCR、自動改 code、GUI、LLM 直連。xls 未解析（v1 PDF-only）。

## Round1 — PT GmbH

來源：`/home/box/Downloads/PT_InvoiceSample/*.msg` → 已解出 PDF 於 `/workspace/msg_extract/**/*.PDF`。

| status | PDF | invoice_no | amount | items | verdict |
|--------|-----|------------|--------|-------|---------|
| PASS | 50656407.PDF | 50656407 | 10091.68 | 12 | pass |
| PASS | 50656462.PDF | 50656462 | 10958.4 | 5 | pass |
| PASS | 50656463.PDF | 50656463 | 2506.32 | 1 | pass |
| PASS* | 50656831.PDF | 50656831 | 114354.38 | 330 | conflict（大檔明細加總差 ~3%） |
| PASS | 50656853.PDF | 50656853 | 87166.76 | 14 | pass |
| PASS | 50661052.PDF | 50661052 | 29587.2 | 1 | pass |
| PASS | 50661078.PDF | 50661078 | 5221.44 | 2 | pass |

**7/7 抽出 invoice_no**；6/7 硬校驗 pass。詳見 `reports/round1_pt.md`。

## Round2 — BHC mega

來源：`/home/box/Downloads/BHC_invoice_samples_mega/`（Mega 已備妥）。

| status | PDF | invoice_no | amount | items | format | notes |
|--------|-----|------------|--------|-------|--------|-------|
| PASS | 3000214469_…Versanddokument.pdf | 200167553 | 37041.41 | 5 | bitzer_v1 | 對上已知金標 |
| NEEDS_GOLD | GDHJ-250980…台湾博世 12-26.pdf | — | — | 0 | — | 有文字層；未種子格式 |
| NEEDS_GOLD | JCH-TW_VKT25097_….pdf | — | — | 0 | — | 同上 |
| NEEDS_GOLD | JCH-TW_VKT25098_….pdf | — | — | 0 | — | 同上 |
| NEEDS_GOLD | SD(TW)_20260126_MEH6A036….pdf | — | — | 0 | — | 同上 |
| NEEDS_GOLD | 台湾博世 26020900066 DOCS.pdf | — | — | 0 | — | 同上 |

xls（DF_SFA…、GDHJ…、台湾博世…）v1 跳過。詳見 `reports/round2_bhc.md`。  
未命中供應商可丟 Auditor 產金標／rules patch。

## How to run

```bash
pip install -e /workspace/PDF_LayoutText
pip install -e /workspace/InvoiceExtractor
python3 -m invoice_extractor --init-db
python3 -m invoice_extractor path.pdf --out out.json
python3 -m invoice_extractor path.pdf --gold gold.json
pytest -q
```

口語說明：`README.md`（繁中）。

## Failures / known gaps

1. **50656831**（58 頁）：明細加總與 header 差 ~3% → hard-check conflict；invoice_no／header amount 仍正確。
2. **非 BITZER 的 BHC mega PDF**（JCH／GDHJ／MEH／台湾博世）：文字層有，但 v1 未種子 format → `needs_gold`（預期行為）。
3. **xls** 未做。
4. VBA Gloria paste 形狀 ≠ pdftotext layout；PT 以 layout 為準。

## GitHub

- URL: https://github.com/Dejureka/InvoiceExtractor
- Branch `main` pushed（`175513c` v1 code；後續 REPORT 更新繼續 push）
- 曾試 `--private`，帳號把 repo disable；已改回 **public** 才能推。若要 private，請在有額度的 org/plan 下改 visibility。

## Auditor note

Auditor id=`87eb5fb7-863d-4404-8489-9b16d6c8ef69`。本地 CLI `--gold` 只做欄位 diff + 硬校驗；語意對帳與新廠商金標交給 Auditor。
