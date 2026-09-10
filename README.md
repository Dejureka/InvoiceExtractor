## 審核 SOP

規則抽出後必經人工／Auditor：見 [`docs/sop/AUDIT_REVIEW.md`](docs/sop/AUDIT_REVIEW.md)。

# InvoiceExtractor

本地可攜的發票 PDF → **Excel (.xlsx)** 抽取器（規則庫 + 硬校驗）。公司電腦拷資料夾就能跑；沒網路也能用已學會的 format。預設輸出 Excel；需要 JSON 時把 `--out` 設成 `.json` 即可（Auditor／自動化仍可用）。

## Windows 免安裝包（推薦）

從 [Releases / portable-latest](https://github.com/Dejureka/InvoiceExtractor/releases/tag/portable-latest) 下載 `InvoiceExtractor_Portable_Win64.zip`，解壓後：

1. **整個資料夾**複製到電腦或隨身碟
2. **雙擊 `InvoiceExtractor.exe`** → 開啟圖形介面（不會只閃一下 console）
3. 拖放或「Browse」選擇 PDF → 可選輸出路徑（預設 `<pdf_stem>.extract.xlsx`）→ 按 **Extract**
4. 摘要顯示：invoice_no、amount、item count、format_id、checker_verdict

命令列（仍可用）：

```bat
InvoiceExtractor.exe path.pdf
InvoiceExtractor.exe path.pdf --out out.xlsx
InvoiceExtractor.exe path.pdf --out out.json
```

手動觸發打包：GitHub → Actions → **Build portable Windows** → Run workflow。

---

## 開發者：從原始碼執行

```bash
# 依賴 layout 文字層
pip install -e /workspace/PDF_LayoutText
pip install -e ".[gui]"
# 或
pip install -r requirements.txt
```

初始化規則庫（會寫入 `data/invoice_formats.db`，含 BITZER + PT Gloria 種子）：

```bash
python -m invoice_extractor --init-db
```

### GUI

```bash
python -m invoice_extractor
# 或
python -m invoice_extractor --gui
# 或
python run_gui.py
```

### CLI

```bash
# 抽一張 → 預設旁輸出 Excel（<pdf_stem>.extract.xlsx）
python -m invoice_extractor path.pdf

# 指定 Excel 路徑
python -m invoice_extractor path.pdf --out out.xlsx

# 仍可輸出 JSON（副檔名 .json）— Auditor／自動化
python -m invoice_extractor path.pdf --out out.json

# 跟金標比（離線，走 checker）
python -m invoice_extractor path.pdf --gold gold.json

# 強制格式
python -m invoice_extractor path.pdf --format bitzer_v1 --out out.xlsx
python -m invoice_extractor path.pdf --format pt_gloria_v1 --out out.xlsx
```

Excel 工作簿含三個工作表：`header`（單列欄位）、`items`（明細列）、`meta`（format_id / checker_verdict 等）。輸出 schema 見 `DESIGN.md`（header / items / meta）。金額會轉成小數（歐式 `6.052,400` → 6052.4）。

## 內建格式

| format_id | 廠商 | 備註 |
|-----------|------|------|
| `bitzer_v1` | BITZER / BHC Versanddokument | 從 BHC_HeaderExtract 移植，樣本 3000214469 |
| `pt_gloria_v1` | Robert Bosch Power Tools GmbH（PT/Gloria） | 用 `pdftotext -layout` 真輸出訓練 |

未命中或文字層空 → `meta.needs_gold` / `needs_ocr`，並寫 placeholder 給人補金標。

## 測試

```bash
pytest -q
```

## Auditor

對帳／語意檢查可丟給 Auditor bot（獨立服務）。本套件本地只做硬校驗。

## 授權

內部工具；樣本發票勿公開推送。
