# FormatSOP — 新增一種發票抽取規則

**溝通名稱：`FormatSOP`**  
路徑：`docs/sop/ADD_INVOICE_FORMAT.md`  
對象：開發／維護規則的人（含 Grok Bot）。  
相關：審核見 [`AUDIT_REVIEW.md`](AUDIT_REVIEW.md)；日常操作見 [`USER_RUN.md`](USER_RUN.md)（溝通名稱 **`RunSOP`**）。

---

## 目標

為一種新的發票版式（或同一廠商的大改版）新增可離線執行的規則：能正確分類、抽出 Summary／Lines、硬校驗可擋假 pass，並留下可追溯的版次紀錄。

---

## 名詞

| 用語 | 意思 |
|------|------|
| `format_id` | 規則識別名，例如 `pt_gloria_v1`、`bitzer_v1`。對應 Python 模組 `src/invoice_extractor/formats/<id>.py`。 |
| **種子（seed）** | 把「這版規則的名片」寫進 SQLite（`data/invoice_formats.db`）：廠商、aliases、`version`、`match_hints`、`rules_json`、備註。由 `--init-db`／`seed_builtin_formats` 執行。種子 ≠ 另寫一套執行引擎；真正抽欄位的是模組裡的 `extract`／`match_score`。 |
| `match_score` | 依檔名＋內文關鍵字打分（0～1）。執行時在 `BUILTIN` 清單裡**每個 format_id 各自打分**，取最高且 ≥ 0.3 者。 |
| v1／v2 | 版式大變時開新模組（如 `pt_gloria_v2`）＋ DB `version=2`，**不覆蓋**舊版。目前沒有「先認廠商再選版次」的第二層；v1／v2 若同時存在，也是兩邊都打 `match_score`，誰高用誰（錨點必須能分開舊／新版式）。 |

---

## 流程（10 步）

### 1. 收樣本

- 至少 1～3 張 PDF（正常＋邊界）。
- 若公司既有 `PDFextract.xlsm`，標註對應 VBA Sub（例：PT → `PT_PDFextract`／`PT_Declaration`；MA 變體很多，一次只對一個 Sub＋樣本）。

### 2. 抽文字層

- 用工具內建文字層（優先 pdftotext／poppler；否則後備）產出對照用 `.txt`。
- **不要只看 PDF 畫面**；規則對的是文字座標／排版字串。

### 3. 定錨點（分類）

- 寫 `MATCH_HINTS`＋`match_score`：廠商名、發票號型態、獨特標題（如 `Ladeliste`、`Net invoiced value of goods`）。
- 檔名與內文加減分；明顯是他家的關鍵字要扣分，避免誤吃。

### 4. 寫 Summary／header 規則

- Invoice No、標籤總額（如 `Final amount`、`Net invoiced value of goods`）、GW（**Gross 不是 Net**）、Packages、Incoterm、Currency 等。
- 金額優先錨在「標籤總額」，不要誤用單價列。

### 5. 寫 Lines／明細規則

- 欄位對齊匯出：`PN`／`Des`／`Qty`／`Unt`／`Amt`／`UoM`／`Co`／`HS code`／`N.W.`／`InvoiceNumber`／`Currency`。
- 與 packing／序號／裝箱列分開，避免把包裝列當商業明細。

### 6. 硬校驗（防假 pass）

- 有標籤總額時：`header.amount` 與 `sum(Lines)` 都必須對上該標籤（容差內），否則 **fail**。
- LINE／QTY 與明細列數／數量一致；自洽但錯的抽出（例如只抓 1 行單價）不得判 pass。

### 7. 登記種子（seed）＋版次

- 新增／更新 Python 模組，並掛進 `rules_engine.BUILTIN`。
- 跑種子把該版寫入 DB（新廠商或新 `version`）；**禁止為了圖方便覆寫舊 version 的語意**。
- 大改版 → 新 `format_id`（`*_v2`）＋新 DB version，舊票仍可對舊規則。

### 8. 跑樣本驗收

- 看 Excel：`Summary` 一列／`Lines` 明細；對人眼與文字層。
- 依 **AuditSOP**：產出 JSON **與 invoice 頁面圖** 給 Auditor（圖文對照）；**硬校驗 pass ≠ 最終收件**，人／Auditor 點頭才算。

### 9. 寫進文件

- 在本 FormatSOP 或模組 `NOTES` 註記：錨點、已知陷阱、對應 VBA Sub 名稱、樣本檔名。

### 10. （可選）發 portable

- 日常可只推 `main`。要給同事免安裝包時再打 Windows portable（內建 poppler／範本）。

---

## 現有 format 速查（錨點印象）

| format_id | 主要錨點（摘要） |
|-----------|------------------|
| `pt_gloria_v1` | `Robert Bosch Power Tools GmbH`、`Invoice No.`、`Net invoiced value of goods`；對齊 VBA `PT_PDFextract`／`PT_Declaration` |
| `bitzer_v1` | `BITZER`、`Ladeliste`、`Commercial Invoice`、`Final amount` |
| `nidec_v1` | `NIDEC TECHNO MOTOR`、`Invoice No. VKT…` |
| `hangji_v1` | Hangji／`GDHJ-…` |
| `hitachi_gls_v1` | Hitachi GLS／`MEH…` |
| `highly_v1` | HIGHLY／海立、`INV#` |

**MA**：xlsm 內有多個 `MA_PDFextract*`／`MA_Declaration*` 變體；**尚未**進本工具規則庫。新增時一次只做一個變體＋樣本。

---

## 完成定義（Definition of done）

- [ ] 樣本抽出 Summary／Lines 正確（含 GW＝Gross、金額＝標籤總額）
- [ ] 假抽出（少行／誤單價）硬校驗會 fail
- [ ] 模組已掛 `BUILTIN`；DB 已種子登記且未覆蓋舊版語意
- [ ] NOTES／本 SOP 有錨點與陷阱說明
- [ ] （若要給現場）portable 另開任務打包

---

## 修訂紀錄

| 日期 | 說明 |
|------|------|
| 2026-09-10 | 初版：與使用者復盤後定稿；澄清種子與 v1／v2 選法 |
