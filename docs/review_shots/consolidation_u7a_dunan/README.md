# Consolidation U7a — dunan: no more `24782` / `EIGHT PALLETS` case values

Branch `consolidate/u7a-dunan-pkg-gw` (on top of U6). FormatSOP bug fix (fragility audit #4).

## What changed
- `dunan_v1.extract_from_text` now reads pkg / GW with the file's own `parse_packing` (the TOTAL row reader the split-PKL path already used): `TOTAL:N PALLETS|PACKAGES|…` and the `N PCS  GW  NW  CBM` sum row.
- Removed: `24782\s*PCS` (one shipment's quantity) and `PACKED IN EIGHT PALLETS → 8`. Replaced by a shared count-word reader `numwords.en_count` (ONE…NINETY-NINE) used only when no TOTAL row exists.
- The anchorless "first ####.## ####.##" guess stays as last resort, still marked by `fallback()` (needs_gold).

## Value changes (all checked against the PDF text / xlsx cells)
Regression 8 batches: **none** (hard 0, diff 0). Whole corpus: 6 docs, all dunan packing lists read standalone:

| Document | Field | Before → After | Document says |
|---|---|---|---|
| BHC 6th case11 PL `…FT00044376.pdf` (+ fixture `c11_dunan_pl.txt`) | GW | 2764 → **9526** | sum row `44644 PCS 9526.00 8405.00 38.16`; 2764 was pallet group 2 of 3 — **was wrong**; needs_gold flag from U5 disappears |
| fixture `c11_dunan_pl_xlsx.txt` | GW | empty → 9526 | same sheet total |
| BHC 6th case3 PL `…FT00044339.pdf` (+ fixture `c3_dunan_pl.txt`) | total_pkg | empty → **35** | `TOTAL:35PACKAGES` (the old rule only knew PALLETS) |
| fixture `c3_dunan_pl_xlsx.txt` | pkg / GW | empty → 35 / 4676 | `TOTAL:35PACKAGES 6140 PCS 4676 …` |

FT00044266 (the `24782` shipment) unchanged: pkg 8, GW 3326, now via the TOTAL row.
In the paired CLI flow these PLs already went through `parse_packing`, which is why the regression batches do not move.

Full diff: `/workspace/invoice-samples/review/consolidation_u7a/corpus_diff.txt`. Tests: `tests/test_numwords_dunan.py` (synthetic).
