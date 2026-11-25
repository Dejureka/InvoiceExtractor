# Consolidation U4 — shared `fallback()` marker, step A (note only)

Branch `consolidate/u4-fallback-note` (on top of U3).

## What changed
- New `src/invoice_extractor/fallback.py`: `fallback(field, value, rule)` returns the value unchanged and remembers which **unanchored** rule produced it (a whole-text guess: first `N PALLETS` anywhere, largest weight, bare invoice-number prefix…). `apply_format` and the PKL merge in `pairing.py` write the hits to `meta.notes` as `fallback[<field>]=<rule>`.
- `FLAG_FALLBACKS = False` → step A writes **notes only**. Step B (U5) turns it on so the field also goes into `needs_gold_fields`.
- Rules routed through it (fragility audit §4.5 list):

| Where | Field | Rule name |
|---|---|---|
| dunan_v1 | total_pkg | `dunan:packed_in_eight_pallets` (case value; removed in U7) |
| dunan_v1 | gross_weight_kg | `dunan:first_weight_pair_anywhere` |
| sumitronics_hk_v1 | invoice_no / invoice_date | `bare_ST_number_anywhere` / `first_date_anywhere` |
| suzhou_aichi_v1 | invoice_no / total_pkg / GW | `bare_SATJG_anywhere` / `first_PLTS_anywhere` / `largest_kgs` |
| shanghai_nature_v1 | total_pkg / GW | `first_PALLET_anywhere` / `first_KGS_anywhere` |
| bhc_vendor_ci_v1 (jiangnan PL) | total_pkg | `jiangnan:cartons_no_pallet_word` (no pallet word → carton count) |
| bhc_my_hub_v1 | invoice_no / invoice_date | `bare_902_anywhere` / `first_date_anywhere` |
| pairing generic PKL parser | GW / pkg | `pkl:hitachi_total_pallets_weight_guess`, `pkl:last_thousands_weight`, `pkl:first_gross_label_anywhere`, `pkl:first_packages_label_anywhere` |

Not routed (deliberately): aichi bare `AETW` and hitachi_gls `MEH…date` — the primary rule never hits there, so flagging would mark every document; they get a structural fix instead (U7 MEH).

## Evidence
- Regression 8 batches: hard 0, **diff 0**. Full `extracts.json` vs main: identical except **1 note** (bhc6 `9027847785…xlsx`: `fallback[invoice_date]=bhc_my_hub:first_date_anywhere` — the 1/17 date fallback the audit predicted).
- Whole sample corpus (448 text-layer docs, cached text): **0 value / flag changes**, 9 docs gain a note (2 dunan PLs + 2 fixtures GW, sumitronics PDF date, 2 suzhou arrival notices + 1 fixture invoice no./pkg, my_hub xlsx date). Full list: `/workspace/invoice-samples/review/consolidation_u4/corpus_diff.txt`.
- `tests/test_fallback.py` (synthetic text): value unchanged, note always, flag only when step B is on. pytest (GUI smoke deselected): 532 passed, 17 skipped (tesseract).
