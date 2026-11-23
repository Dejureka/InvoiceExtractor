# Auditor review — saginomiya T262288 (singular `pc.` line)

**format_id:** `bhc_vendor_ci_v1`（profile=`saginomiya`，既有 format，沒有新 id）  
**Branch:** `fix/saginomiya-pc-uom`（尚未併進 main，等 Auditor pass）  
**Sample:** `/workspace/bhc-plan/inbox/20261123_KLG-T26L74Y/att/T262288.pdf`（發票＋packing list 合訂，有文字層）

## 改了什麼

明細列的數量單位原本只認 `pcs.`，第 22 項印的是單數 `1 pc.`，整列被丟掉，抽出 27 行。現在改成通用單位：`pc`／`pc.`／`pcs`／`pcs.`（大小寫皆可）。沒有對這張發票寫特例，G.W. 規則沒動（PL Total 列是淨重 1,374.09 kg → 發票 G.W. 留空＋附註用 BL G.W.）。

## 預期合計（發票 p.3 Total）

| 欄位 | 預期 | 抽出 |
| --- | --- | --- |
| LINE | 28 | 28 |
| QTY | 12,075 | 12,075 |
| Invoice Value | JPY 7,606,228 | 7,606,228 |
| Packages | 6 Pallets（Package Total: 138 Cartons / 6 Pallets） | 6 |
| G.W. | 空白，用 BL G.W. 1,613 kg | 空白＋Summary 附註 |
| Incoterms | FOB YOKOHAMA | FOB YOKOHAMA |

第 22 項：PN `1EC07199A`，Des `PRESSURE SWITCHES Type DNS-D606MQ`，Qty 1，Unt 2,676，Amt 2,676，UoM PCS，Co Japan。與 BHC gold `InvoiceLines_KLG-T26L74Y.xlsx` **28 列逐欄差異 0**。

本箱沒有 tesseract，B/L `20261118160446-0001.pdf` 是掃描檔，沒有抽提單；發票 G.W. 依既有規則留空。BL G.W. 1,613 kg 請對 B/L 頁面人工確認。

## 截圖與 Result

- 第 22 項裁圖：[`crops/line22_T262288.png`](crops/line22_T262288.png)（來源 [`inv-3.png`](inv-3.png)，發票第 3 頁）
- 合計區裁圖：[`crops/totals_T262288.png`](crops/totals_T262288.png)（Total 12,075 pcs.／F.O.B ¥7,606,228；Package Total 138 Cartons／6 Pallets）
- Result 列：[`result_rows.md`](result_rows.md)
- 抽出 JSON：[`T262288.extract.json`](T262288.extract.json)
- validate_result：[`findings.md`](findings.md)

## validate_result

`hard = 0`，`warn = 29`：

- `W_GW_FROM_BL` × 1：發票無毛重、附註要用 BL G.W.（既有 saginomiya 規則，與 T261565 相同）
- `W_HS_MISSING` × 28：發票未印稅號（BHC 缺 HS 只警告）

沒有其他警告。

## 回歸

- `tests/test_gold_regression.py`、`tests/test_validate_result.py`、BHC 4th／5th／6th 測試：232 passed、8 skipped。新建測：`test_saginomiya_t262288`（layout fixture）＋`test_saginomiya_singular_pc_unit_parses`（`pc.`／`pc`／`pcs.`／`pcs`／`PC.`／`PCS`／`Pc.`）。既有 `test_saginomiya_t261565` 仍過。
- `tools/regression_batches.py --baseline out/regress/baseline`：八批 **diff = 0**（ma3 184、pt4 23、bhc4 14、bhc5 2、bhc6 19、ebike1 18、soe2 10、maak 3）。OCR 跳過與基線相同，不算差異。
- 既有鷺宮樣本：
  - **T261565**（BHC 6th case10，`T261565.pdf`＋`fixtures/bhc6/c10_saginomiya.txt`＋`tests/gold/bhc6.json`）：CLI 抽出 LINE 25／QTY 9,854／JPY 7,433,872／pkg 5／G.W. 空白，Result 欄位與 gold 一致。
  - **T261955**（KLG-T26I2N7）：掃描件、無文字層，本箱無 tesseract，CLI 為 `ocr_failed`／needs_gold，無法在本箱重跑。

請審第 22 項裁圖、合計區，以及 Result 的 28／12,075／7,606,228。
