# Auditor pack — MA HS + RB packages/GW fix

**Date:** 2026-09-11 16:38 PT  
**Focus:** (1) Line HS filled for GEH/Brake Fluid (and all lines); (2) Summary Packages / G.W. from unique RB × Gross.

## Fixes

### A) HS codes
`find_hs_after_item` in `ma_common.py` (shared by `ma_with_period_v1` + `ma_no_period_v1`):
- Scan after each line-item until next pos/PN line (max 55 lines) for `HS CODE <digits>`
- Fixes GEH Brake Fluid with many Dispatch element rows (HS was at offset 8; old window stopped at 7) and NP page-break HS

### B) Packages + Gross weight
`parse_rb_packages(text)`:
- Regex: `\bRB\s+(\d{6,})\b` then `Gross\s+([\d,.]+)\s*KG` within same line / next 2 lines
- `total_pkg` = **count of unique RB numbers** within that invoice PDF
- `gross_weight_kg` = **sum of first Gross KG per unique RB** (same RB again ignored)

## Debug 2120525526 (before → after)

| field | before | after |
|-------|--------|-------|
| Line PN `1.987.479.202.GEH` qty 1800 HS | empty | **38190000** |
| All 6 lines HS | 5/6 | **6/6** |
| Packages | null | **12** |
| G.W. kg | null | **5163.84** |
| Goods value / currency | 624749 / TWD | same |

Unique RBs in PDF: 200317596/606/608/609/611/612/613/615/617/619/651/652 (12).

## Batch

- MA invoices: **27** (WP 6, NP 21)
- hard_check: **27 pass / 0 fail**
- HS complete (every line has HS): **27/27**

JSON: `out/ma_fix_hs_rb/json/` · Excel: `out/ma_fix_hs_rb/MA_fix_hs_rb_batch.xlsx`  
Shots: `docs/review_shots/ma_fix_hs_rb/` (also `auditor_pack/shots/`)

## Spot set for this audit

| invoice | JSON | shots to check |
|---------|------|----------------|
| **2120525526** (debug) | `MA_WP_INVOICE_2120525526.json` | p02-hs (Brake Fluid + HS CODE 38190000), p03–p05-rb (RB … Gross KG) |
| 2120414558 | `MA_WP_INVOICE_2120414558.json` | p1/p2, goods, rb pages |
| 2120411708 | `MA_WP_INVOICE_2120411708.json` | p1/p2, goods, rb |
| 2000262902 | `MA_NP_…2000262902….json` | p1, goods, rb marking |
| 2000263342 | `MA_NP_…2000263342….json` | p1, goods, rb |

## Ask

Per invoice: **pass / conflict / needs_gold**.

Please verify especially:
1. **2120525526** Lines: PN `1.987.479.202.GEH` Des Brake Fluid Qty 1800 → HS **38190000** (not empty)
2. Summary **Packages** = unique RB count; **G.W.** = sum of those RBs’ Gross KG (match packing/RB pages)
3. Other spot JSONs: HS filled on lines; Packages/GW coherent with RB×Gross on shots

Return pass/conflict per file.
