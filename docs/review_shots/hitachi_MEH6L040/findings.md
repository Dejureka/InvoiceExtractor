# validate_result — MEH6L040

## 1. 只跑發票 PDF（INV+PKL 同一檔）

```
python3 tools/validate_result.py Result.xlsx --extract-json MEH6L040.extract.json --out findings.xlsx
```

結果：**hard = 0，warn = 0**（exit 0）。沒有任何 finding。
（HS code 欄圖面沒有印，BHC 缺 HS 屬 soft；hitachi_gls_v1 不輸出 HS，validator 未提出 W_HS_MISSING。）

## 2. 整個資料夾（INV PDF + Waybill 掃描檔 + 空白 xls）

- `SSLJP0034204　MEH6L040.xls`：空白 Excel 範本，CLI 依既有規則 skip（不進 Result）。
- MEH6L040 列：hard 0。
- `20261120110024.pdf`（Cosmo Trans Line Waybill 261120KEE101，掃描檔）：本箱沒有 Tesseract，OCR 失敗 → `H_OCR_FAILED` ×1 + `H_HDR_MISSING` ×6、`W_NEEDS_GOLD_FLAG`、`W_NO_LABELED_TOTAL`。這是環境限制（掃描 BL 依分工由 BHC bot 目視），跟 hitachi_gls_v1 修改無關；main 上結果相同。
  - 目視 waybill：2 PALLETS, 19 CARTONS（21 PACKAGES）、931.000 KGS、9.288 M3、INVOICE NO. MEH6L040 —— 與修後 Result 的 Packages 21 / GW 931 一致。
