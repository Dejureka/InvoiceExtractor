# Auditor pack — Round4b (MA WithPeriod currency fix re-audit)

**Date:** 2026-09-11 (Asia/Taipei / PT)  
**Why:** Round4 Auditor conflict — PDF shows **Amount in TWD** but `ma_with_period_v1` left `header.currency` / `item.currency` null. Also packing-only end pages were insufficient (need **Goods value** labeled-total pages).

## Fix

`ma_with_period_v1._currency` now accepts split header rows (`Amount` / `Discount … in TWD`), `Amount TWD` on declaration pages, and plain `in TWD`.

## Materials

| set | files |
|-----|-------|
| MA_WP JSON (5) | `MA_WP_INVOICE_2120….json` (also `json/`) |
| MA_WP shots | p1, p2, **`pNN-goods.png` (Goods value page)**, last packing page |
| MA_NP goods shots (2) | `0011263371_…_p14-goods.png`, `0020029837_…_p37-goods.png` |

Full batch JSON still under `out/round4/json/` (MA_WP refreshed). Mirror: `out/round4b/`.

## Ask (re-audit)

For the 5 MA WithPeriod invoices, return `pass` / `conflict` / `needs_gold` with:

- currency **TWD** on header + lines vs image (`Amount … in TWD` / `Amount TWD`)
- amount = **Goods value** on `*-goods.png` vs JSON
- invoice_no / item_line_count / Incoterm as usual
- Do **not** pass if goods-total page missing or figure/JSON disagree

Invoices: 2120411708, 2120397792, 2120408063, 2120406484, 2120414558.
