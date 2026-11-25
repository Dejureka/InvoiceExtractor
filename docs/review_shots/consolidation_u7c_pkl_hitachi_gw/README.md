# Consolidation U7c — generic PKL: no more "prefer 1174" GW guess

Branch `consolidate/u7c-pkl-hitachi-gw` (on top of U7b). FormatSOP bug fix (fragility audit #6).

## What changed
- `pairing.parse_packing_pkg_gw`, branch `(TOTAL: N PALLETS …`: GW used to be "every ###.## in the text, 50–50000, prefer ≈1174 or 1000–2000". Now: GW = the 2nd weight column of item rows shaped `… {qty} {NW} {GW} {CBM}` (header `SETS KGS. CLM.`), summed over item rows, TOTAL lines skipped. No such row → GW stays empty (no guess). Pallet count unchanged.
- That branch no longer goes through `fallback()` (U4/U5 rule `pkl:hitachi_total_pallets_weight_guess` is gone) because it now reads a column instead of guessing.

## Value changes
- None found. Regression 8 batches: diff 0. All 594 cached text layers through the PKL parser: 0 changes.
- The only real document on this path is BHC 3rd case8 `PACKING LIST (BOSCH).pdf` (scan). OCR'd once with tesseract 5.5 (installed temporarily, then removed so the box stays as before): row `HITACHI INDUCTION MOTOR 38 977.50 1,174.00 1.556`, `(TOTAL: 2 PALLETS` → **2 / 1174.0**, same as before and as the Auditor-confirmed figure. OCR text kept privately: `/workspace/invoice-samples/unit/ocr_text/bhc3_case8_PACKING_LIST_BOSCH.tesseract5.txt`.

Tests: `tests/test_pkl_hitachi_gw.py` — synthetic (one row, a non-1174 weight, two rows summed, no row → None) + private check on the real OCR text.

Side note: with tesseract present, `tests/test_bhc_6th.py::test_case8_original_3page_scan_end_to_end` fails on **main** too (2 pair rows instead of 1) — environment-dependent OCR, not caused by this branch.
