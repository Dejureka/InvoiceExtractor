## SOP（溝通用名稱）

| 名稱 | 檔案 | 用途 |
|------|------|------|
| **FormatSOP** | [`docs/sop/ADD_INVOICE_FORMAT.md`](docs/sop/ADD_INVOICE_FORMAT.md) | 怎麼新增一種發票規則 |
| **RunSOP** | [`docs/sop/USER_RUN.md`](docs/sop/USER_RUN.md) | 怎麼操作工具（多檔／範本／輸出） |
| **AuditSOP** | [`docs/sop/AUDIT_REVIEW.md`](docs/sop/AUDIT_REVIEW.md) | 抽出後人工／Auditor 審核 |

# InvoiceExtractor

本地可攜的發票 PDF → **Excel (.xlsx)** 抽取器（規則庫 + 硬校驗）。公司電腦拷資料夾就能跑；沒網路也能用已學會的 format。預設輸出 Excel；需要 JSON 時把 `--out` 設成 `.json` 即可（Auditor／自動化仍可用）。

**輸出統一**：不論單檔或多檔，預設都寫入工具最外層根目錄的 **`InvoiceExtract_Result.xlsx`**（含 `InvoiceExtractor.exe` 的資料夾；開發時為專案／範本所在根目錄）。每次執行載入固定範本 `data/templates/InvoiceExtract_Template.xlsx`、**清掉舊資料列**、再寫入本次結果（單／多發票同一檔）。可用 Browse／`--out` 覆寫。不再預設在 PDF 旁產生 `<pdf>.extract.xlsx`。

## Windows 免安裝包（推薦）

從 [Releases / portable-latest](https://github.com/Dejureka/InvoiceExtractor/releases/tag/portable-latest) 下載 `InvoiceExtractor_Portable_Win64.zip`，解壓後：

1. **整個資料夾**複製到電腦或隨身碟（含 `poppler/bin`，勿只拷 exe）
2. **雙擊 `InvoiceExtractor.exe`** → 開啟圖形介面（不會只閃一下 console）
3. 拖放或「Browse」選擇 **一個或多個** PDF（也可「Add folder」）→ 可選輸出路徑（預設工具根目錄的 `InvoiceExtract_Result.xlsx`）→ 按 **Extract**
4. 摘要顯示：`invoice_no | format_id | mapping status | hard pass/fail`（`audit ok`／`已知未審`／`全新／需規則`／`hard fail`）；批次統計在底列；失敗檔另列
5. 本包**已內建 poppler**；若摘要出現 text backend 警告，請確認 `poppler/bin/pdftotext.exe` 仍在同一資料夾

命令列（仍可用）：

```bat
InvoiceExtractor.exe path.pdf
InvoiceExtractor.exe a.pdf b.pdf --out InvoiceExtract_Result.xlsx
InvoiceExtractor.exe C:\invoices_folder
InvoiceExtractor.exe path.pdf --out out.json
```

手動觸發打包：GitHub → Actions → **Build portable Windows** → Run workflow（push `main` 相關路徑亦會自動重建 `portable-latest`）。

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

Browse 可多選 PDF；Add folder 可加入整個資料夾；拖放多個 PDF／資料夾亦可。輸出預設為工具根目錄（exe 旁／專案根）的 `InvoiceExtract_Result.xlsx`（同檔覆寫）。 選檔後 GUI 顯示 **INV＋PKL 配對表**（BHC `_INV_`／`_PKL_` 分檔為主；MA 合訂本一次抽完）；Extract 前可改配／拆開／略過。詳見 RunSOP。

### CLI

```bash
# 單檔或多檔 → 預設寫入工具根目錄 InvoiceExtract_Result.xlsx（清列再寫）
python -m invoice_extractor path.pdf
python -m invoice_extractor a.pdf b.pdf
python -m invoice_extractor ./invoices_dir

# 指定 Excel 路徑（每次用固定範本清列再寫）
python -m invoice_extractor path.pdf --out out.xlsx

# 仍可輸出 JSON（副檔名 .json）— Auditor／自動化；多檔時寫入 <stem>_json/ 目錄
python -m invoice_extractor path.pdf --out out.json

# 跟金標比（離線，走 checker；僅單檔）
python -m invoice_extractor path.pdf --gold gold.json

# 強制格式
python -m invoice_extractor path.pdf --format bitzer_v1 --out out.xlsx
python -m invoice_extractor path.pdf --format pt_gloria_v1 --out out.xlsx
```

BL / 到貨通知 / HBL：

- 發票模式：配對表含 **提單**；Summary 右側新增 `BL No.` / `BL Packages` / `BL G.W. (kgs)`（不覆寫發票 Packages/G.W.）
- 專用 BL 工作表（可選）：

```bash
python -m invoice_extractor --doc-type bl arrival.pdf --out BLExtract_Result.xlsx
python -m invoice_extractor --doc-type bl arrival.pdf --out bl.json
```


部分失敗時：成功的發票仍會寫入 Excel；CLI／GUI 會清楚列出失敗檔。

Excel 工作簿採 **PDFextract.xlsm 風格欄位**（範本：`data/templates/InvoiceExtract_Template.xlsx`；Summary 含 `BL No.`／`BL Packages`／`BL G.W. (kgs)`；內部 JSON schema 給 Auditor 用）：

| 工作表 | 說明 |
|--------|------|
| **`Summary`** | 每張發票一列（各自合計，非跨檔加總）：Invoice No. / Packages / Package Mode / G.W. (kgs)-Air DIM. (CBM)-Sea / Incoterms / Invoice Value / LINE / QTY / Invoice Currency |
| **`Lines`** | 明細：PN / Des / Qty / Unt / Amt / UoM / Co / HS code / N.W. / InvoiceNumber / Currency |
| **`meta`** | 每檔一列：format_id / checker_verdict / text_backend / status / error 等 |

`--out *.json` 仍寫完整內部 schema（header / items / meta）。金額會轉成小數（歐式 `6.052,400` → 6052.4）。

### 文字層（可攜包已內建 poppler）

優先用 **poppler `pdftotext -layout`**（可攜包內 `poppler/bin/pdftotext.exe`，不必另裝）。若找不到，才退到 pymupdf / pdfminer；GUI 與 `meta.text_backend_warning` 會明確警告，不會默默降級而不告知。BITZER 規則已能在無 pdftotext 時從 Final amount + 多行明細抽出 5 列／37041.41，但 PT 等格式仍以 pdftotext 佈局為準。

### OCR 後備（掃描件／文字層空）

當 `pdftotext`／後備文字層為空（`needs_ocr`）時，會離線呼叫 **Tesseract** 把頁面光柵化後 OCR，再把文字送進**同一套** `rules_engine`（**沒有**獨立的 OCR `format_id`）。

- `meta.text_backend` = `ocr/tesseract` 表示走了 OCR
- GUI Summary 會顯示 `OCR used: ocr/tesseract`；啟動時會探測 tesseract 是否可用
- 開發機：`apt install tesseract-ocr tesseract-ocr-eng`（或 Windows 安裝 [UB Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki)），並確保 `tesseract` 在 PATH；也可用環境變數 `TESSERACT_CMD` / `TESSDATA_PREFIX`
- **Windows 實驗包**：見 Release tag [`portable-ocr-test`](https://github.com/Dejureka/InvoiceExtractor/releases/tag/portable-ocr-test)（**不是** `portable-latest`）。該 zip 在 poppler 之外另含 `tesseract/`（`tesseract.exe` + `tessdata`）。日常正式包 `portable-latest` **不含** OCR。

驗 OCR 路徑（掃描 PDF）：

```bash
python -m invoice_extractor /path/to/scan.pdf --out /tmp/ocr_test.json
# meta.text_backend 應為 ocr/tesseract
pytest -q tests/test_ocr.py
```

### OCR 成可搜尋／可複製 PDF（獨立工具）

掃描件可另外匯出帶文字層的 PDF（**不**跑發票 Extract）：

- GUI：**「OCR 成可複製 PDF」** → 多選掃描 PDF → 背景執行 → 結果寫入工具根目錄旁的 **`ocr_out/`**（自動建立；檔名 `{原檔名}.ocr.pdf`）
- CLI：`python -m invoice_extractor --ocr-pdf a.pdf b.pdf`（`--out` 可指定輸出目錄）
- 語言：預設 `eng`；若 tessdata 有 `chi_tra`／`chi_sim` 會自動一併使用
- `ocr_out/` 在使用前為空；產出為使用者檔案，非大型安裝內容

## 內建格式

| format_id | 廠商 | 備註 |
|-----------|------|------|
| `bitzer_v1` | BITZER / BHC Versanddokument | 從 BHC_HeaderExtract 移植，樣本 3000214469 |
| `pt_gloria_v1` | Robert Bosch Power Tools GmbH（PT/Gloria） | 用 `pdftotext -layout` 真輸出訓練 |

未命中 → `meta.needs_gold`。文字層空會先試 Tesseract OCR；仍空或無 tesseract → `needs_ocr`／placeholder。OCR 成功則 `text_backend=ocr/tesseract` 並走同一規則引擎。

## 測試

```bash
pytest -q
```

## Auditor

對帳／語意檢查可丟給 Auditor bot（獨立服務）。本套件本地只做硬校驗。

## 授權

內部工具；樣本發票勿公開推送。
