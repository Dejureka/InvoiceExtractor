# Round4b — MA WithPeriod currency fix

**Date:** 2026-09-11 (Asia/Taipei)

## Bug

Auditor Round4: PDF column header is visual **Amount in TWD**, but layout text splits it across two rows (`Amount` then `Discount … in TWD`). Strict `Amount\s+in\s+TWD` left `header.currency` and all `item.currency` **null** for all 5 WithPeriod invoices.

## Fix

`src/invoice_extractor/formats/ma_with_period_v1.py` `_currency`: accept split headers, `Amount TWD`, `Discount in TWD`, and `in TWD`.

## Result

All 5 re-extracted with `currency=TWD`, hard_check **pass**. Pack: `docs/review_shots/round4b/`.
