# Auditor review — bhc_my_hub_v1 發票號 9028 開頭抽不到

**format_id:** `bhc_my_hub_v1`（既有 format，沒有新 id）  
**Branch:** `fix/bhc-my-hub-9028-invoice-no`（尚未併進 main，等 Auditor pass）

## 樣本

| 發票號 | 來源 INV | 配對 PKL |
| --- | --- | --- |
| 9028194267 | `/workspace/bhc-plan/inbox/20261125_TPE261127/att/BHCWHYTW2611005_INV_9028194267.PDF` | `PKL_BHCWHYTW2611005 台湾 世邦 空运.pdf` |
| 9028111779 | `/workspace/bhc-plan/inbox/20261115_SHAKEL26N72963/att/BHCWHYTW2611001_INV_9028111779.PDF` | `PKL_BHCWHYTW2611001 台湾 世邦.pdf` |

兩張都有文字層（`pdftotext -layout`），不是掃描檔。

## 改了什麼

`pdftotext -layout` 的表頭是「標籤列 → 下一列寫公司名＋發票號＋日期」。舊規則在發票號前面只准 80 個字元，實際公司名加空白是 **84** 個字元，所以主規則對現有 MY-HUB 樣本從來沒對上過。9027 開頭的舊票能抽出來，全靠備援規則寫死 `9027`；9028 開頭就變成 `invoice_no` 空白、`needs_gold`。

這次做的是通用修正，沒有對這兩張發票寫死號碼：

1. 主規則改成在「Invoice Number: / Invoice Date:」的下一整列找「10 位數字 + 日期」，不再用 80 字元上限。
2. 備援改認 MY-HUB 的 10 位 `902xxxxxxx` 家族；優先取「旁邊有日期」的那個，避免先抓到 HS／PO／交貨參考號。
3. 檔名比對同樣從 `9027` 放寬成 `902xxxxxxx`。
4. 疊在下一行的 `Invoice Number:`（pdfminer／pymupdf 讀序）原本的 `\s*` 規則仍保留。

同一規則也抽出了 inbox 裡另外兩張 9028 票（`9028047245`、`9028073720`）以及既有 9027 樣本，號碼沒有寫進規則。

## 預期 vs 抽出（INV+PKL）

| 發票號 | 欄位 | 圖面 | 抽出 |
| --- | --- | --- | --- |
| 9028194267 | Invoice Number | 9028194267 | 9028194267 |
|  | Invoice Date | 25.11.2026 | 2026-11-25 |
|  | TOTALS | 17,140.80 USD | 17,140.80 |
|  | LINE / QTY | 2 列／480 PCS | 2／480 |
|  | pkg／GW | 來自 PKL | 2／376.00 kg |
|  | Incoterms | CIF Taipei | CIF Taipei |
| 9028111779 | Invoice Number | 9028111779 | 9028111779 |
|  | Invoice Date | 12.11.2026 | 2026-11-12 |
|  | TOTALS | 219,865.30 USD | 219,865.30 |
|  | LINE / QTY | 29 列／11,211 PCS | 29／11,211 |
|  | pkg／GW | 來自 PKL | 648／7,186.68 kg |
|  | Incoterms | CIF Taipei | CIF Taipei |

只丟 INV、不配 PKL 時，發票號一樣抽得到；pkg／GW 依既有規則留空（這個 format 原本就是 soft-missing packing/GW OK）。checker 兩邊都是 `pass`。

## 截圖與 Result

- 發票號裁圖：[`crops/invoice_no_9028194267.png`](crops/invoice_no_9028194267.png)、[`crops/invoice_no_9028111779.png`](crops/invoice_no_9028111779.png)
- Result 列：[`result_rows.md`](result_rows.md)
- 抽出 JSON：[`9028194267.extract.json`](9028194267.extract.json)、[`9028111779.extract.json`](9028111779.extract.json)
- validate_result：[`findings.md`](findings.md)
- 回歸：[`regression.md`](regression.md)

## validate_result

INV+PKL 的 Result + extract JSON：`hard = 0`，`warn = 31`，全部是 `W_HS_MISSING`（這兩張發票 HS CODE 欄是空的；BHC 缺 HS 只警告）。沒有其他警告。

## 測試與回歸

- 新增 `tests/test_bhc_my_hub_invoice_no.py`（6 筆）：兩張 9028 layout fixture、視窗寬於 80 且號碼不是 9027、stacked 標籤且不誤抓 PO／交貨號、既有 9027 fixture、檔名 `INV_9028…` 仍加分。
- pytest：515 passed、20 skipped、3 failed。3 筆失敗是既有的 `tests/test_gui_smoke.py`（本箱沒有 `tkinter`），與這次修改無關；既有 `test_my_hub_unchanged`／xlsx twin 仍過。
- `tools/regression_batches.py` 對 main 基線八批 **diff = 0**（ma3 184、pt4 23、bhc4 14、bhc5 2、bhc6 19、ebike1 18、soe2 10、maak 3）。

請審兩張裁圖上的發票號／日期，以及 Result 的 9028194267（2／480／17,140.80）與 9028111779（29／11,211／219,865.30）。
