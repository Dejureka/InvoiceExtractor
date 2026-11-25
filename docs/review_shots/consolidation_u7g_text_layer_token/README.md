# Consolidation U7g — OCR-vs-text-layer choice: document-number shape, not `9027…`

Branch `consolidate/u7g-text-layer-token` (on top of U7f). Fragility audit #19.

## What changed
`text_layer.ocr_text_looks_more_reliable`: when OCR shows a `TOTAL N PALLETS` the text layer lacks, OCR is preferred only if both texts share a document number (same document). That number used to be one of `USDI…|VKT…|9027xxxxxx|OK########` — so a MY-HUB `9028…` file or any other vendor never qualified. Now any document-number-shaped token qualifies: 8–12 digits, or 2–6 letters + 5–12 digits.

## Value changes
- Regression 8 batches: diff 0 (the box has no tesseract, so OCR paths are not exercised by the batch run).
- The one real document known to use this path, BHC 3rd case8 `PACKING LIST (BOSCH).pdf`: still prefers OCR (shared `USDI4105369`) — checked with its real text layer + the cached tesseract 5.5 text (private test).
- Synthetic: `9028…` and `AB1234567` now behave like `9027…` (these 2 cases fail on the old code); different numbers or a layer with its own pallet total keep the layer.
- **Not measured:** other scanned PKLs in real runs with OCR (Windows portable). A broader token can only switch OCR on when the layer has no pallet total and OCR does, for the same document number.

Tests: `tests/test_text_layer_doc_token.py`.
