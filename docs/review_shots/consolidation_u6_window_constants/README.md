# Consolidation U6 — window limits as named constants + 80 % margin test

Branch `consolidate/u6-window-constants` (on top of U5).

## What changed
- New `src/invoice_extractor/windows.py`: the 22 fixed look-ahead / gap limits (MA HS 55 lines, AK 45 / 25, COO 5000 chars, eBike/PT/SOE/BITZER/Hitachi/NIDEC windows, two generic-PKL gaps), each with which format uses it and what it bounds. Formats read `windows.NAME` at call time. Same numbers as before → pure move.
- New `tests/test_window_margin.py` (private samples): for each constant, run the documents of the formats that use it normally and with the limit at 80 %; every Result field (Summary + Lines) and `needs_gold_fields` must stay the same. A coverage test makes sure every constant in `windows.py` is in the test.
- Corpus for the test: cached text layers of all 594 text-layer samples on the box, `/workspace/invoice-samples/unit/window_corpus/` (private, in the manifest).

## Results
- **Refactor diff 0**: regression 8 batches hard 0 / diff 0, full `extracts.json` identical to U5; whole corpus (448 classified docs) 0 changes.
- 80 % test: **19 limits have ≥ 20 % margin; 3 do not** (marked `xfail(strict=True)` so they must be removed from the list once fixed):

| Limit | Value | Documents that change at 80 % | Fix |
|---|---|---|---|
| `MA_HS_LINES_AFTER_ITEM` | 55 | 1 (RBTW 2000271108: item across a page needs 48) | U7: stop at the next item only |
| `MA_AK_LINES_AFTER_ITEM` | 45 | 7 (AK00067724 needs 38; AK00074096/7 fixtures) | U7: stop at next item / Marking only |
| `HITACHI_GLS_DESC_LINES` | 3 (i+1..i+2) | 2 (MEH6L040: description two lines under the row) | small integer; 80 % = 2 removes one of two lines. Leave for Auditor (already raised on MEH6L040) |

- Not failing although audit called them tight: BITZER invoice-no gap (177/200 needed, but a structural `no/date/date` fallback catches it), MA_WP COO index (2904/5000).
- pytest: 20 passed + 3 xfailed for the margin test (6 s); CI without samples: skipped.
