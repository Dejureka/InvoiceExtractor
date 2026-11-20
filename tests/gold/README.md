# Result goldens

These snapshots freeze the current extractor's Summary and Lines values and
format IDs for the Auditor-reviewed MA 3rd, PT 4th, BHC 4th–6th, eBike 1st, SOE
2nd, and MA AK 74096 shipment. Each file is a JSON array. MA 3rd is split across numbered files
to keep each file below 300 KB without dropping Result fields.
`test_gold_regression.py` re-extracts the source inputs and checks every stored
field, with a reason and exact occurrence count for each known hard finding.

The frozen scope is reproducible without Tesseract. It excludes OCR-dependent
invoices and packing lists, invoices marked `needs_gold`, and OCR-dependent BL
cells. Native-text invoices with an omitted OCR BL contribute their other
Result fields. The MA AK source is the repository's three PDF layout text
fixtures. The batch runner reports which inputs require OCR and compares the
remaining fields with the snapshots in `docs/review_shots/`.
