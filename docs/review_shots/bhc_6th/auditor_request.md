# Auditor request — BHC 6th batch (2026-10-08)

**Scope:** 15 shipments (15 .msg) from `/home/box/Downloads/BHC-batch-6th/`, unpacked to
`BHC_6th data/case1…15`. Case 8 runs only invoice MEH6K018 + waybill 261002KEE602. That was the
user's decision: waybill 261002KEE601 and its marks sheet were misplaced by the forwarder, have no invoice,
are recorded as skipped and are not output.

**Branch:** `feature/bhc-6th` (not pushed / not merged). Commit: see `git log -1 feature/bhc-6th`.

**Pack:** this folder.
- `auditor_batch_summary.md`: per-case table, needs-check items, user decisions, soft notes, hard-check notes,
  rule changes and the regression result.
- `caseN__<file>/page_XXXX.png`: page images. Excel files are rendered as `…_xls` / `…_xlsx`.
- `crops/`: key-field crops.
- `caseN_INV_*.json` / `caseN_BL_*.json`: full extracts. The `_hard` key holds the hard-check result.
- `index.json`: files per case.

## Please verify

1. **Per invoice:** invoice no., amount (= labeled total = sum of lines), LINE/QTY, pkg/GW and
   BL No./pkg/GW against the page images and crops, for all 15 cases.
2. **Needs check: case 8 BL GW.** It is `needs_gold` (blank) because the OCR reads under the waybill hatch
   don't agree. The image shows **50.000 KGS** (= INV/PL 50). See
   `crops/case8_bl_pkg_gw_NEEDS_CHECK.png` and `crops/case8_bl_gw_50.000_clip_NEEDS_CHECK.png`.
   Please confirm the gold value: 261002KEE602 / 1 / 50.
3. **New profiles.** The new `bhc_vendor_ci_v1` profiles are topband (cases 1–2), augewei (12), jiangnan (13),
   wolong (14–15) and saginomiya (10). Check the PN source column and the origin rules
   (case 10 per line; cases 13 and 15 blank because origin is not printed).
4. **User-approved soft decisions.**
   - Cases 14 and 15: the numeric TOTAL is used instead of the mismatching amount in words, with a note.
   - Case 10: invoice G.W. is blank because the PL Total row is Net Weight; there is a Summary note and BL G.W. is 1,460.9.
5. **BL fixes.**
   - TVL `SHAKEL26C72175` (case 12) and `SHAKEL26C71898` (case 13) are output in full.
   - Case 9 waybill pkg is 6 (4 PALLETS + 2 CASES; it was 4).
   - Case 11 PL GW is 9,526 (the generic parser took 2,764).
   - Case 10 Ocean Links waybill `KLG-T268Y98`.
6. **Regression delta, BHC 3rd case 5 (Dunan FT00044266).**
   - The INV↔PL pairing via Chinese filenames now gives 2 rows with 8 / 3,326.
   - Before, it gave 4 rows: INV rows had blank pkg/GW and the PL files appeared as their own rows.
   - The new output matches the audited BHC 3rd gold.
   - All other 31 regression folders (BHC 2nd/3rd/4th/5th + mega) are identical to `main`.

## Known limits (not changed in this batch)

- **Single-PL twins:** when there are PDF + Excel twins and only one PL, pkg/GW is filled on one twin row only
  (cases 5, 6, 9). This matches BHC 2nd case 5/8 and 4th case 3.
- **Observed in BHC 2nd, left unchanged:** the PDF row PN of 9027451705 reads `CC0009213B       C-DEN-ZU`,
  while its xlsx twin has `CC0009213B`. It was left as audited to keep earlier outputs unchanged;
  the Excel-only PN split added for case 5 does not touch PDFs.

Please reply per case: pass / fix (with field and gold value).
