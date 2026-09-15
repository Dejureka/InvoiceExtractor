# BHC cases BL / 到貨通知 / HBL — FormatSOP audit pack

**Date:** 2026-09-15 (Asia/Taipei)  
**Scope:** text-layer only (no OCR). Arrival-notice / HBL / B/L PDFs from BHC cases 1–8.  
**Summary:** adds `BL No.` / `BL Packages` / `BL G.W. (kgs)` after invoice Packages/G.W. (never overwrites invoice pkg/GW).  
**Also:** dedicated Excel **`BL`** sheet + JSON (`doc_type: bl`) via `--doc-type bl`.

## Layout families (not one-per-forwarder)

| format_id | Family | Cases / files |
|-----------|--------|---------------|
| `ceva_pyramid_arrival_v1` | 捷飛運通 / CEVA / Pyramid Lines **到貨通知** | case4 `到貨 448.pdf`, case5 `到貨 449.pdf`, case6 `到貨 298.pdf` |
| `dhl_lcl_arrival_v1` | DHL GF Taiwan **海運 LCL 到貨通知** | case2 `到貨通知 - NGOA23259.pdf` |
| `hippopo_hbl_v1` | Hippopo **HBL draft** | case3 `HBL draft HB26090012….pdf` |

## Extract results

| case | file | format_id | bl/hbl | vessel / voy | ETA | pkg | GW (kg) | inv refs | hard |
|------|------|-----------|--------|--------------|-----|-----|---------|----------|------|
| 2 | 到貨通知 - NGOA23259.pdf | `dhl_lcl_arrival_v1` | NGOA23259 (MBL NGOKEL260806173) | TS MAWEI / 2616S | 2026-08-23 | 5 CAS | 3560 | JCH26-08M1 | pass |
| 3 | HBL draft HB26090012….pdf | `hippopo_hbl_v1` | HB26090012 | YM INAUGURATION / 343S | — | 12 PALLETS | 7217 | AETW26012 | pass |
| 4 | 到貨 448.pdf | `ceva_pyramid_arrival_v1` | WEB260166448 | MATOYA BAY / 0N81JN1NC | 2026-08-22 | 99 PLT | 17095.54 | — | pass |
| 5 | 到貨 449.pdf | `ceva_pyramid_arrival_v1` | WEB260166449 | CNC LEOPARD / 0N81HN1NC | 2026-08-23 | 33 PLT | 6052.14 | — | pass |
| 6 | 到貨 298.pdf | `ceva_pyramid_arrival_v1` | WEB260169298 | WAN HAI 286 / N112 | 2026-08-29 | 3 CASE | 867 | — | pass |

## Summary BL columns (invoice mode pairing)

Demo workbook: `docs/review_shots/bhc_bl_cases/Summary_with_BL_Result.xlsx`

| case | Invoice No. | Packages / G.W. (invoice) | BL No. | BL Packages | BL G.W. |
|------|-------------|---------------------------|--------|-------------|---------|
| 3 | AETW26012 | 12 / 7217 | HB26090012 | 12 | 7217 |
| 6 | 9027519666 | 3 / 867 | WEB260169298 | 3 | 867 |
| 4 | 9027451705 | — / — (no PKL text) | WEB260166448 | 99 | 17095.54 |
| 5 | 9027451746 | — / — | WEB260166449 | 33 | 6052.14 |
| 2 | (BL-only; INV scan) | — | NGOA23259 | 5 | 3560 |

## Skipped (no text-layer BL PDF)

| case | reason |
|------|--------|
| 1 | No BL PDF (only `.msg` + `QDEX2609010.jpg`) |
| 7 | Scan-only PDFs (`likely_scan`); MSG mentions NBT309 |
| 8 | No BL PDF (scan `20260904…` + INV/PKL); MSG mentions HBL SHAKEL26770270 |

## Materials

- JSON: `docs/review_shots/bhc_bl_cases/*.json` (also `out/bhc_bl_cases/json/batch_json/`)
- Excel BL sheet: `BLExtract_Result.xlsx`
- Excel Summary+BL: `Summary_with_BL_Result.xlsx`
- Shots: `case*_*.png` (DHL includes p1+p2)

## CLI

```bash
python -m invoice_extractor --doc-type bl path.pdf --out BLExtract_Result.xlsx
python -m invoice_extractor inv.pdf 到貨.pdf --out InvoiceExtract_Result.xlsx
```

## UI

GUI pairing: `配對 | INV | PKL | 提單 | 狀態`.

## Auditor checklist

Confirm figure vs JSON for: BL/HBL no, vessel/voyage, ETA, packages + unit, Gross GW, shipper/consignee snippets, invoice refs when present (DHL/Hippopo). Confirm Summary BL columns ≠ invoice Packages/G.W. Hard pass ≠ final accept.
