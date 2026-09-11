# Auditor pack — MA RB unique-key = first+optional second segment

**Date:** 2026-09-11 16:55 PT  
**Focus:** Fix NoPeriod RB unique key: concatenate the two number segments after `RB` (e.g. `RB 40670214025622` + next-line `6531` → `406702140256226531`). WithPeriod single-segment (`RB 200317606`) unchanged.

## Before → after (conflict case)

| invoice | field | before (first-segment only) | after (concat when 2nd present) |
|---------|-------|-----------------------------|----------------------------------|
| **2000262902** (NP) | Packages | **22** | **67** |
| **2000262902** | G.W. kg | **3570.29** | **7885.48** |
| **2120525526** (WP) | Packages | 12 | **12** (unchanged) |
| **2120525526** | G.W. kg | 5163.84 | **5163.84** (unchanged) |

## Rule (`parse_rb_packages` in `ma_common.py`)

- Match `RB` + first long digits + optional second digit group (same line **or** immediately next line alone).
- Unique key = `first+second` if second present, else `first`.
- Gross KG associated with that unique key; duplicate keys ignore repeat weight.

## Batch

- MA invoices: **27** (WP 6, NP 21)
- hard_check: **27 pass / 0 fail**
- HS complete: **27/27**

JSON: `out/ma_fix_rb_concat/json/` · Excel: `out/ma_fix_rb_concat/MA_fix_rb_concat_batch.xlsx`  
Also refreshed under `out/ma_fix_hs_rb/`.

## Spot / shots

| invoice | JSON | shots |
|---------|------|-------|
| **2000262902** | `MA_NP_…2000262902….json` | **full RB pages p44–p56** `*_pNN-rb.png` (two-segment markings visible) |
| **2120525526** | `MA_WP_INVOICE_2120525526.json` | p03–p05-rb (single-segment still 12 / 5163.84) |

## Ask

Per invoice: **pass / conflict / needs_gold**.

Please verify especially:
1. **2000262902** Summary Packages=**67**, G.W.=**7885.48** — unique keys are concat of both RB number segments (not first only). Cross-check several p44–p56 RB blocks.
2. **2120525526** still Packages=**12**, G.W.=**5163.84**.
3. Other NP samples with repeated first segments must not collapse packages.
