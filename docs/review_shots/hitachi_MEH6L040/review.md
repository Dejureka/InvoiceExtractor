# Auditor review — hitachi_gls_v1 MEH6L040 conflict（BHC 回報 4 處）

**format_id:** `hitachi_gls_v1`（既有 format，擴充，沒有新 id）
**Branch:** `fix/hitachi-gls-meh6l040`（尚未併進 main，等 Auditor pass）

## 樣本

| 檔案 | 說明 |
| --- | --- |
| `/workspace/bhc-plan/inbox/20261125_261120KEE101/att/20261126_MEH6L040 (TY09,TY32, TY81, TY91, TY98).pdf` | INV p1 + PKL p2 + 明細 p3，有文字層（`pdftotext -layout`） |
| `.../att/20261120110024.pdf` | Cosmo Trans Line Waybill 261120KEE101（掃描檔，本箱無 Tesseract → OCR 失敗，不在本次修正範圍） |
| `.../att/SSLJP0034204　MEH6L040.xls` | 空白 Excel 範本，CLI 依既有規則 skip |

BHC 人工正確值：`/workspace/bhc-plan/extract/20261125_261120KEE101/gold_manual.json`（已複製到 `fixtures/bhc_hitachi_MEH6L040/MEH6L040_gold.json`）。
我先用 `pdftotext -layout` + 頁面圖逐欄核對 gold，**gold 與 PDF 全部一致**（7 列合計 2,741,527 = GRAND TOTAL；451 PCS；21 PACKAGES；GW 931）。

## 四個問題的根因與修法（皆通用規則，無寫死案例值）

| # | 問題 | 根因 | 修法 |
| --- | --- | --- | --- |
| 1 | 第 6 行 `P-AP90DNA*EX` 漏抽，明細合計 2,702,162 | 不是 SUB TOTAL 擋住；是 inline 列的料號 regex `[A-Z][A-Z0-9][A-Z0-9/.\-]*` 要求第 2 字元是英數（這顆是 `-`），而且不允許 `*` | 料號允許第 2 字元為 `-`（後面須接英數）、允許 `*` 變體後綴 |
| 2 | Packages 只抓 2 | PKL `TOTAL :` 列只有 PALLETS 數 2；`CARTONS / 19` 與 `21 PACKAGES` 印在下面幾行，舊規則只取 TOTAL 列第一個數 | TOTAL 列之後 8 行內若有印出的 `N PACKAGES`（且 ≥ TOTAL 列數）就用它；沒有的話把「單位標籤行 + 純數字行」（CARTONS/CASES/PALLETS…）加總 |
| 3 | RPC-4.0FSR 品名抽成 `MADE IN JAPAN`、RPC-5.0FSR 抽成料號 | 品名行跟左邊 Marks & Numbers 欄共用同一文字行；舊規則把整行 strip 後判斷，`MADE IN JAPAN`（嘜頭）被當品名，`P80016921 … INDOOR UNIT` 因開頭有嘜頭不合格 | 從該列「項次欄位」那一欄往右切出文字當品名；切出來是空的（只有嘜頭）就看下一行；遇到 PO 行／下一列／TOTAL 停 |
| 4 | Co 全部 JP | `PSH-4,PC-ARFG2-T,P-AP90DNA*EX -ORIGIN: CHINA` 這行因 `*` 不符合 per-model origin regex，整行沒吃到，全部退回 `OTHERS -ORIGIN: JAPAN` | origin 清單的字元集加上 `*` |

## 預期 vs 抽出（INV+PKL）

| 欄位 | gold / 圖面 | main（修前） | branch（修後） |
| --- | --- | --- | --- |
| Invoice No. | MEH6L040 | MEH6L040 | MEH6L040 |
| Packages | 21 | 2 | **21** |
| G.W. | 931 | 931 | 931 |
| Incoterms | FOB（圖面 F.O.B. SHIMIZU, JAPAN） | F.O.B. SHIMIZU, JAPAN | F.O.B. SHIMIZU, JAPAN（與已審 MEH6J044/MEH6K018 同寫法，未改） |
| Invoice Value | 2,741,527 | 2,741,527（明細只 2,702,162 → conflict） | 2,741,527（明細合計相等） |
| LINE | 7 | 6 | **7** |
| QTY | 451 | 446 | **451** |
| Currency | JPY | JPY | JPY |

Lines（branch 輸出，與 gold 逐欄相同）：

| PN | Des | Qty | Unt | Amt | Co |
| --- | --- | --- | --- | --- | --- |
| PSC-6RAD | ACCESSORY : RAC ADAPTOR | 180 | 3,588 | 645,840 | JP |
| PSH-4 | ACCESSORY: SERVICE CHECKER | 2 | 17,756 | 35,512 | **CN** |
| PC-ARFG2-T | ACCESSORY: WIRED REMOTE CONTROLLER | 240 | 4,590 | 1,101,600 | **CN** |
| RPC-4.0FSR | **INDOOR UNIT** | 12 | 61,084 | 733,008 | JP |
| RPC-5.0FSR | **INDOOR UNIT** | 2 | 61,066 | 122,132 | JP |
| **P-AP90DNA*EX** | **ACCESSORY: PANEL** | 5 | 7,873 | 39,365 | **CN** |
| TRF-NP160U1 | ACCESSORY: RENEWAL KIT | 10 | 6,407 | 64,070 | JP |

checker：main `conflict` → branch `pass`。

## 裁圖

- 第 6 行在 SUB TOTAL 之後：[`crops/line6_after_SUB_TOTAL.png`](crops/line6_after_SUB_TOTAL.png)
- RPC 品名與左側嘜頭：[`crops/descriptions_RPC.png`](crops/descriptions_RPC.png)、整段明細 [`crops/items_block_marks_column.png`](crops/items_block_marks_column.png)
- 原產地兩行：[`crops/origin_lines.png`](crops/origin_lines.png)
- PKL 件數（2 PALLETS + 19 CARTONS = 21 PACKAGES）：[`crops/packages_total.png`](crops/packages_total.png)

## 其他資料

- Result 列：[`result_rows.md`](result_rows.md)
- 抽出 JSON：[`MEH6L040.extract.json`](MEH6L040.extract.json)（修前：[`MEH6L040.before_main.extract.json`](MEH6L040.before_main.extract.json)）
- validate_result：[`findings.md`](findings.md)
- 回歸：[`regression.md`](regression.md)

## 測試

- 新增 `tests/test_hitachi_gls_meh6l040.py`（7 筆）：MEH6L040 fixture 的 Summary / Lines 對 gold 逐欄比對；`*` 料號的 origin 清單；件數「印出 PACKAGES」、「沒有 PACKAGES 行時加總」、「單一單位不變」；合成樣本（`*` 料號 + 嘜頭共用行 + 泰國產地，不同數值）防寫死。
- 既有 `test_hitachi_gls_inline_accessory_layout`（MEH6J044）、`test_hitachi_gls_old_layout_unchanged`（MEH6A036）、`test_hitachi_meh6k018_label_next_line`（MEH6K018）照過。
- pytest：522 passed、20 skipped、3 failed（既有 `tests/test_gui_smoke.py`，本箱沒有 `tkinter`）。

請審四張裁圖對 Result：第 6 行、RPC 兩列品名、CN 三列、Packages 21。
