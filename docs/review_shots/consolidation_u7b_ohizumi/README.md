# Consolidation U7b — ohizumi: cartons from "<words> (N) CARTONS", not `TWENTY-TWO`

Branch `consolidate/u7b-ohizumi-pkg` (on top of U7a). FormatSOP bug fix (fragility audit #5).

## What changed
- `ohizumi_dongguan_v1`: `TWENTY-TWO (22) CARTONS → 22` replaced by any count word followed by `(N) CARTONS` → N (shared `numwords`). If the words and the digits disagree, the digits are used and the field is marked by `fallback()` (needs_gold). TOTAL-row rules (PDF / Excel PL) still win when present, as before.

## Value changes
Regression 8 batches: none. Whole corpus: **1 document**:

| Document | Field | Before → After | Document says |
|---|---|---|---|
| bhc-plan inbox CPSE26110673 `(發票)…26609A….pdf` | total_pkg | empty → **24** | `TOTAL :TWENTY-FOUR (24)CARTONS` ✔ (U3 issues #2) |

26575 invoice stays 22. After merge, drop the `total_pkg` exclusion for this file in `/workspace/invoice-samples/gold/cov8.json` (kept now so the U3–U7a branches still pass their gold test).

Tests: `tests/test_count_words.py` (synthetic: 22 / 24 / 9 cartons).
