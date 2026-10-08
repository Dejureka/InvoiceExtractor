# BHC 6th — Auditor round 2 (2026-10-08)

Round-1 review @ecf69bb: 14 cases pass, case 8 needs fixes
(`out/bhc_6th_auditor_review.md`). Branch `feature/bhc-6th` (not pushed, not merged).

## Case 8 now runs the ORIGINAL forwarder scan

`BHC_6th data/case8/run/` holds the files as the user drops them:
- `Shipping Docs 20261005 MEH6K018_TW.pdf` (invoice)
- `20261002094338-0001.pdf`: the original 3-page scan. p1 is waybill 261002KEE601, p2 its marks sheet, p3 waybill 261002KEE602.

The cropped `…_p3_KEE602.pdf` is no longer used. It was moved to `BHC_6th data/_review/`.
`selection.json` was updated, and the test fixture is now the OCR of the 3-page original
(`fixtures/bhc6/c8_jif_waybill_3page_ocr.txt`; the cropped-p3 fixture was removed).

### Output (Result row)

| Invoice No. | Amount | LINE / QTY | pkg / GW | BL No. | BL pkg | BL G.W. | verdict |
|---|---|---|---|---|---|---|---|
| MEH6K018 | JPY 294,030 | 2 / 20 | 1 / 50 | **261002KEE602** | **1** | **50** | **pass** (no needs_gold) |

Row note: `bl_waybill=261002KEE602 (p3, printed INVOICE NO. matches MEH6K018; other waybill(s) in the file not used: 261002KEE601 p1-2)`.

### Per-waybill reads (`case8_BL_20261002094338-0001.json` → `meta.documents`)

| waybill | pages | INVOICE NO. reads (one-line re-reads) | pkg | GW cell re-reads (12 = 300/400/600 dpi × hatch removal 0/2/3/4) | result |
|---|---|---|---|---|---|
| 261002KEE601 | p1–2 | MEH6KO19, MEHGKO19 ×4, MEHGKOT9 → folded MEH6K019 / MEH6K0T9 (0 of 6 match MEH6K018) | 5 (marks sheet only, needs_gold) | 745 ×6, 745.006/.008 ×3, 748 ×2, – ×1 → integer 745 (9) / decimals .000 (8): 745 (8 of 12) | **not used** (no invoice in this batch) |
| 261002KEE602 | p3 | MEH6KO18 ×2, MEH6K018 ×4 → folded MEH6K018 (6 of 6 match) | 1 (SAY ONE(1) PALLET + case no.; 3 reads) | 50.006 ×4, 50 ×5, 40 ×3 → integer 50 (9) / decimals .000 (8): **50** (8 of 12) | **selected** |

The waybill no. comes from the page passes plus the bottom-anchored one-line re-read of the `…KEE…` token
(KEE602 6/6, KEE601 6/6).

### Crops (`crops/`)

- `case8_r2_p3_KEE602_gw_50.png`: Gross Weight (KGS) **50.000** under the hatch stamp
- `case8_r2_p3_KEE602_invoice_no.png`: `INVOICE NO. MEH6K018`
- `case8_r2_p3_KEE602_waybill_no.png`: `261002KEE602`
- `case8_r2_p3_KEE602_say_pkg.png`: `SAY :ONE(1)PALLET ONLY.-`
- `case8_r2_p1_KEE601_invoice_no.png` (`MEH6K019`), `case8_r2_p1_KEE601_waybill_no.png`,
  `case8_r2_p1_KEE601_gw_745.png` (745.000), `case8_r2_p1_KEE601_say_pkg.png`: the unused waybill, for comparison
- Page images: `case8__20261002094338-0001/page_0000…0002.png`

## What changed

1. **Multi-waybill BL PDF** (`jif_cosmo_waybill_v1`)
   - **Splitting pages into waybills:** the OCR pages are split on `\f`. Each face page (`Gross Weight` / `Measurement` / `Waybill No.` / `NON-NEGOTIABLE`) starts a waybill. A page without a face (a marks sheet) belongs to the waybill before it.
   - **Reads per waybill:** each waybill is voted on its own: BL no., pkg, GW (attached-sheet case no. included). The printed `INVOICE NO.` is read in the goods description: the label is located, extended right over the same OCR line, and re-read as one line (psm 7) at 3 dpi × 2 cleanings.
   - **Header and flags:** when more than one waybill no. is found, the header BL No./pkg/GW stays blank with needs_gold. The per-waybill values go to `meta.documents`. A single-waybill PDF behaves as before.
2. **Waybill selection at pairing** (`pairing.select_bl_document`, called in `extract_pair_row`)
   - **Matching:** both sides are normalised for OCR look-alikes (O/Q/D→0, I/L/|→1, G→6, S→5, B→8, Z→2). The invoice no. matches a waybill when ≥2 of its reads match **and** no other waybill has any matching read.
   - **On a match:** only that waybill's BL No./pkg/GW is output, its own field flags are carried over, and the unused waybill(s) are named in the notes.
   - **No match or ambiguous:** BL No./pkg/GW stay blank and the row is flagged `bl_no` / `bl_packages` / `bl_gross_weight_kg` needs_gold (nothing guessed). `merge_bl_onto_inv` now flags this case even though no BL value was used.
3. **GW cell re-read** (`_gw_cell_rect` / `_located_reads`)
   - **Locating the cell:** the cell is the first digit row under the `Gross Weight` header in that column. Three page passes each give a box: raw, hatch-removed k=3 and k=4. Their intersection drops hatch fragments merged into the OCR word (`S745,`, `60.00]`, `48,000"`).
   - **Re-reading:** the cell is re-read 12× (psm 8, digits only).
   - **Parsing:** JIFFA weights always print 3 decimals, so the last 3-digit group is the decimals. One trailing hatch digit is ignored.
   - **Voting:** the **integer and decimal parts are voted separately**, each needing ≥2 reads and a strict majority. Hatch noise hits one digit group at a time.
   - **Weight in the GW vote:** a passing cell value counts as 2 reads in the GW vote. That is enough when the page passes find nothing, as in case 8. ≥3 agreeing page/token reads still outvote it.
   - **Truncation guard:** if the cell value is the tail of another read (e.g. `774.5` vs `1774.5`), it is dropped and noted.
   - **Generic logic:** none of this uses case values.
4. **Optional hardening** (no output change on existing data)
   - TVL `SHAKEL26C0#####` phantom glyph: stripped only when a page pass supports the 5-digit form (same last 5 digits). A genuine 6-digit C number is kept, and the `B/L NO.` regexes accept 5–6 digits after `C`.
   - saginomiya filename hint: now only a whole filename `T######.pdf|xls|xlsx` (no more `…T123456.` inside other names).

## Verification

- **Full pytest:** 355 passed, 3 skipped. That includes 10 new round-2 tests in `tests/test_bhc_6th.py`: GW cell parse, component vote, waybill groups, multi-waybill header, selection match / no-match / ambiguous / single-read, merge flag, `line_run`, TVL phantom guard, saginomiya hint, and an end-to-end case 8 test on the original scan (skipped when the scan is absent).
- **Regression BHC 2nd–5th + mega (32 folders) vs `main` @4fab308:** only BHC 3rd case 5 differs. That is the round-1 Dunan PL pairing, which matches the audited gold.
- **BHC 6th vs ecf69bb (review-pack JSONs):** only case 8 changed (`bl_gross_weight_kg` blank → 50, needs_gold → pass; BL file is now the 3-page original). The other 14 cases have identical Result fields. Their BL JSONs only gained `meta.documents: null` and extra re-read notes.
- **Old JIF waybills:** unchanged. BHC 4th case 6, case 8 (`WAYBILL.pdf` 3,084.5) and its scan copy, and 6th cases 9 and 10 all keep their outputs.

## Known limits

- The cell box is an intersection of three OCR boxes. If one pass misses the leading thousands group, the cell reads only the tail. This happened on 6th case 9 (`774.5`). The truncation guard drops it, and the page/token reads (1,774.5 ×5) decide. If no other read existed, such a tail could only be outvoted, not detected.
- KEE601's pkg (5) comes only from its marks sheet (1 read), so it is needs_gold inside `documents`. It is not output.
