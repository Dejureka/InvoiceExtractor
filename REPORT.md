# InvoiceExtractor v1 — Overnight REPORT

**Date:** 2026-09-10 (PT / Asia/Taipei)  
**User / org:** Dejureka  
**Auditor bot:** `87eb5fb7-863d-4404-8489-9b16d6c8ef69`（對帳／語意檢查可丟給 Auditor；本套件本地只做硬校驗）

## What was built

Portable package at `/workspace/InvoiceExtractor`:

| Path | Role |
|------|------|
| `src/invoice_extractor/schema.py` | header + items + meta dataclasses；歐式/美式數字、德式日期 |
| `text_layer.py` | wrap `pdf_layout_text`；空文字 → `needs_ocr` |
| `db.py` | SQLite `vendors` / `formats` / `runs`；`--init-db` 種子 |
| `checker.py` | 硬校驗（行數／qty／amount／幣別／單價×量） |
| `rules_engine.py` | classify + apply format |
| `formats/bitzer_v1.py` | BITZER/BHC，自 BHC_HeaderExtract 移植 |
| `formats/pt_gloria_v1.py` | PT GmbH／Gloria，**用 pdftotext -layout 真輸出訓練**（非 paste VBA） |
| `gold_stub.py` | needs_gold placeholder；`--gold` 離線比對 |
| `cli.py` / `__main__.py` | CLI |
| `data/invoice_formats.db` | 種子 DB（BITZER v1 + PT Gloria v1） |
| `tests/` | schema / checker / bitzer header / PT invoice_no |
| `reports/round1_pt.md` / `round2_bhc.md` | 驗證表 |

**刻意不做（依 DESIGN）：** OCR、自動改 code、GUI、LLM 直連。

**Mega：** 登入過期，未等 Mega；Round2 只用 `/home/box/Downloads/BHC_invoice_samples/`。

## Round1 — PT GmbH

來源：`/workspace/msg_extract/**/*.PDF`（從 PT `.msg` 已抽出）。

| status | PDF | invoice_no | amount | items | verdict |
|--------|-----|------------|--------|-------|---------|
| PASS | 50656407.PDF | 50656407 | 10091.68 | 12 | pass |
| PASS | 50656462.PDF | 50656462 | 10958.4 | 5 | pass |
| PASS | 50656463.PDF | 50656463 | 2506.32 | 1 | pass |
| PASS* | 50656831.PDF | 50656831 | 114354.38 | 330 | conflict（大檔明細加總差，約 3%） |
| PASS | 50656853.PDF | 50656853 | 87166.76 | 14 | pass |
| PASS | 50661052.PDF | 50661052 | 29587.2 | 1 | pass |
| PASS | 50661078.PDF | 50661078 | 5221.44 | 2 | pass |

**7/7 抽出 invoice_no**；6/7 硬校驗 pass。詳見 `reports/round1_pt.md`，JSON 在 `out/round1/`。

## Round2 — BHC / BITZER

| status | PDF | invoice_no | amount | pkg | gw | items | verdict |
|--------|-----|------------|--------|-----|-----|-------|---------|
| PASS | 3000214469_…Versanddokument.pdf | 200167553 | 37041.41 | 7 | 6052.4 | 5 | pass |

與已知金標一致（invoice_no / amount / pkg / weight / 5 lines）。詳見 `reports/round2_bhc.md`。

## How to run

```bash
pip install -e /workspace/PDF_LayoutText
pip install -e /workspace/InvoiceExtractor
python3 -m invoice_extractor --init-db
python3 -m invoice_extractor path.pdf --out out.json
python3 -m invoice_extractor path.pdf --gold gold.json
pytest -q
```

口語說明見 `README.md`（繁中）。

## Failures / known gaps

1. **50656831**（58 頁大發票）：明細 regex 漏／多重複，sum(amount) 與 header 差約 3% → hard-check conflict；invoice_no／amount header 仍正確。
2. **Mega BHC mega 樣本**：未取得；僅單張 BITZER。
3. **VBA Gloria paste 形狀** ≠ pdftotext layout；PT 規則以 layout 為準。
4. 明細 description 欄位有時被兩欄品名黏在一起截斷（v1 可接受）。

## GitHub

- Commit: `175513c` on `main`
- Remote: https://github.com/Dejureka/InvoiceExtractor
- Pushed successfully (repo already existed; visibility set private if permitted).


## Auditor note

Parent 已建立 Auditor bot `87eb5fb7-863d-4404-8489-9b16d6c8ef69`。規則 JSON vs 金標語意對帳可交給該 bot；CLI `--gold` 只做本地欄位 diff + 硬校驗。
