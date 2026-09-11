# RunSOP — InvoiceExtractor 操作說明

**溝通名稱：`RunSOP`**  
路徑：`docs/sop/USER_RUN.md`  
對象：實際跑工具抽發票的同事。  
相關：新增規則見 [`ADD_INVOICE_FORMAT.md`](ADD_INVOICE_FORMAT.md)（**`FormatSOP`**）；審核見 [`AUDIT_REVIEW.md`](AUDIT_REVIEW.md)（可稱 **`AuditSOP`**）。

---

## 你會得到什麼

一次執行（可多張 PDF）產出 **一份** Excel：

| 工作表 | 內容 |
|--------|------|
| `Summary` | 每張發票一列（自己的 Packages／G.W.／Invoice Value／LINE／QTY…） |
| `Lines` | 所有明細列在同一張表，用 `InvoiceNumber` 對回發票 |
| `meta` | 每檔狀態、使用的 format、文字層後端、校驗結果／錯誤 |

固定欄位來自內建範本：`data/templates/InvoiceExtract_Template.xlsx`。  
每次執行會**清掉上次資料列**再寫入（表頭與格式保留）。

多檔預設檔名：`InvoiceExtract_Result.xlsx`。  
單檔若未指定輸出，也可能是 `<檔名>.extract.xlsx`（視版本／參數）。

---

## Windows 免安裝包（有 portable 時）

1. 下載並解壓 `InvoiceExtractor_Portable_Win64.zip`（**整個資料夾**保留，含 `poppler/bin`）。
2. 雙擊 `InvoiceExtractor.exe` → 應出現視窗（不該只閃黑窗）。
3. **Browse** 多選 PDF，或 **Add folder**，或拖檔／拖資料夾進視窗。
4. 輸出路徑可改；多檔預設 `InvoiceExtract_Result.xlsx`。
5. 按 **Extract**。成功看 Summary／Lines；失敗檔會在介面列出。

命令列（可選）：

```bat
InvoiceExtractor.exe a.pdf b.pdf --out InvoiceExtract_Result.xlsx
InvoiceExtractor.exe C:\path\to\invoice_folder
InvoiceExtractor.exe one.pdf --out out.json
```

> 若 `main` 已有新功能但 Releases 尚未重打 portable，以主管／開發告知的版本為準；不要假設舊 zip 已含最新多檔／範本行為。

---

## 開發機／原始碼

```bash
python -m invoice_extractor --gui
python -m invoice_extractor a.pdf b.pdf --out InvoiceExtract_Result.xlsx
python -m invoice_extractor ./invoices_dir
```

首次或規則更新後可：`python -m invoice_extractor --init-db`。

---

## 常見狀況

| 現象 | 建議 |
|------|------|
| 雙擊 exe 黑窗閃一下 | 舊版 CLI-only，或請用命令列帶 PDF；新版應開 GUI |
| 金額像「單價」、明細只有 1 行 | 文字層／規則問題；看 `meta` 的 backend／verdict；換含 poppler 的完整資料夾 |
| G.W. 偏小 | 可能誤抓淨重；回報發票號＋畫面（正確應為 Gross） |
| 某廠商完全抽不到 | 可能尚未有規則（例如多數 **MA** 變體）；走 FormatSOP 開新 format |
| 要給 Auditor | 另存／輸出 `.json`（或依現行參數），見 AuditSOP |

**審核**：要給 Auditor 時依 **AuditSOP**——Tools 需附 JSON＋invoice 圖，不只 txt／JSON。

**原則**：只貼失敗／異常的畫面與對應列，成功的不必整包貼。

### GUI 格式對應狀態（mapping status）

Extract 後 Summary／底列會顯示每張發票的對應狀態（另附 `format_id`、硬校驗）：

| 標籤 | 意義 |
|------|------|
| `audit ok` | 命中已通過 AuditSOP 的 format（見 `data/audited_formats.json`） |
| `已知未審` | 有 format_id，但尚未列入審核通過表 |
| `全新／需規則` | 未命中／needs_gold／空文字層 |
| `hard fail` | 硬校驗 conflict |

範例列：`50666223 | pt_gloria_v1 | audit ok | hard pass`  
批次結尾會統計各標籤筆數。


---

## 修訂紀錄

| 日期 | 說明 |
|------|------|
| 2026-09-11 | GUI 顯示 format mapping status（audit ok／已知未審／全新／需規則／hard fail） |
| 2026-09-10 | 初版：多檔、固定範本、溝通名稱 RunSOP |
