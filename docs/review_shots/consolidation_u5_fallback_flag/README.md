# Consolidation U5 — fallback step B: fallback value ⇒ `needs_gold_fields`

Branch `consolidate/u5-fallback-flag` (on top of U4).

## What changed
- `FLAG_FALLBACKS = True`: a field produced by an unanchored fallback (U4 list) is added to `meta.needs_gold_fields`, and the row gets `needs_gold=True` / `confidence=needs_gold` (same invariant pairing and pt_gloria already use: any needs_gold field ⇒ row needs_gold; the validator raises H_NEEDS_GOLD_FLAG otherwise).
- `NOTE_ONLY_FIELDS = {"invoice_date"}`: invoice_date is not a Result column, so a guessed date keeps the note and does **not** send the Result row to manual review.
- **No value changes** — only flags.

## Exactly which documents gain flags
Regression 8 batches: **none** (hard 0, diff 0, full extracts identical to U4).

Whole sample corpus (448 text-layer docs): 7 docs, 0 value changes:

| Document | Format | Flagged field = value | Checked against the PDF |
|---|---|---|---|
| BHC 3rd case 1 `到貨通知.pdf` | suzhou_aichi_v1 | invoice_no SATJG26010, total_pkg 7 | arrival notice, not an invoice — flag is right |
| bhc-plan inbox CSPE26110311 `到貨通知.pdf` | suzhou_aichi_v1 | invoice_no SATJG26014, total_pkg 3 | arrival notice — flag is right |
| fixture `bhc4/c2_tvl_hbl_ocr.txt` | suzhou_aichi_v1 | invoice_no SATJG26011 | HBL OCR text — flag is right |
| BHC 6th case3 dunan PL `…FT00044339.pdf` (+ fixture `bhc6/c3_dunan_pl.txt`) | dunan_v1 | GW 4676 | total row `6140 PCS 4676.00` — value correct, flag is a false alarm until U7 reads the total row |
| BHC 6th case11 dunan PL `…FT00044376.pdf` (+ fixture `bhc6/c11_dunan_pl.txt`) | dunan_v1 | GW **2764** | **wrong**: total row prints `44644 PCS 9526.00`; 2764 is pallet group 2 of 3 → U7 dunan fix |

Full list: `/workspace/invoice-samples/review/consolidation_u5/corpus_diff.txt`.

## Evidence
- `tests/test_fallback.py`: step B on; flag + needs_gold set; invoice_date stays note-only.
- pytest (GUI smoke deselected): 539 passed, 17 skipped (tesseract).
