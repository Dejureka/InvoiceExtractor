# Consolidation U7f — MA look-ahead windows end at the structure, not at a count

Branch `consolidate/u7f-ma-windows` (on top of U7e). Fragility audit #7, #8, #9.

## What changed (`windows.py` only + tests)
| Limit | Before | After | Real boundary (already in the code) |
|---|---|---|---|
| `MA_HS_LINES_AFTER_ITEM` (ma_no_period / ma_with_period HS) | 55 lines (needed 48) | 400 (runaway cap) | next item row (`_NEXT_ITEM`) |
| `MA_AK_LINES_AFTER_ITEM` (ma_ak_billing desc / HS / origin) | 45 lines (needed 38) | 400 (runaway cap) | next item row / `Marking` |
| `MA_WP_COO_INDEX_CHARS` (ma_with_period COO table) | 5000 chars (needed 2904, grows with items) | 50000 (runaway cap) | next `Country of origin` |

The stop conditions were already there; the fixed counts only cut long items/tables short (an item across a page break, a long COO table). Now the counts are far above any page and only guard against runaway scans.

## Value changes
None: regression 8 batches diff 0; corpus 448 docs 0 changes (no current sample exceeded the old limits — this is margin, not a fix of a present error).
80 % margin test: both MA limits now pass and were removed from the xfail list (remaining xfail: `HITACHI_GLS_DESC_LINES`).
Tests: `tests/test_ma_item_boundary.py` (synthetic: HS 120 lines below an item is found; HS after the next item is never taken).
