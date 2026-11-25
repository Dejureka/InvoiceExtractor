# Consolidation U7d — dunan / oukai invoice date: any month, not only "Sep"

Branch `consolidate/u7d-month-dates` (on top of U7c). FormatSOP bug fix (fragility audit #2, #3).

## What changed
- New shared `schema.EN_MONTH_RE` (Jan…Dec, short and long forms, `Sept`).
- `dunan_v1`: `DATE … Sep 26,2026` rule → `DATE … <any month> d,yyyy` (ISO form unchanged).
- `oukai_v1`: `Date: Sep 21st, 2026` rule → any month.
- Output form unchanged (the printed string, as before).

## Important: invoice_date is not a Result column
The Result Summary columns are invoice_no, total_pkg, package_mode, gross_weight_kg, incoterm, amount, item_line_count, total_quantity, currency, bl_no, bl_packages, bl_gross_weight_kg. Before this fix an October dunan/oukai invoice would **not** have shown a wrong or empty Result cell; it only affects the validator (`H_HDR_MISSING` for an empty date) and `meta`.

## Value changes
None today: every dunan/oukai sample on the box is dated September (dates of all 448 corpus docs + the 8 cov8 invoices compared: 0 changes). Regression 8 batches: diff 0.
Tests: `tests/test_month_dates.py` (synthetic, 13 month spellings × 2 formats).
