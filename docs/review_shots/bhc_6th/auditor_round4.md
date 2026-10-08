# BHC 6th — Auditor round 4 (2026-10-08)

Round-3 review @6400611 (`out/bhc_6th_round3_auditor_review.md`): item 3 still needed fixes; everything else passed.
This round replaces the round-2/3 GW cell voting details with one **simple, conservative rule**, as requested.
Branch `feature/bhc-6th`, not pushed and not merged.

## The rule (`jif_cosmo_waybill_v1._decide_gw`, `_source_value`; `pairing.corroborate_cell_only_gw`)

1. **One vote per independent source.** The sources are:
   - page pass `r1`;
   - hatch-removed page pass `clean`;
   - the token clip, whose 300/400/600 dpi re-reads collapse to ONE value (their strict majority; otherwise the source abstains).

   The located cell (12 re-reads collapsed by the integer/decimals vote) is one more source **only if the widened-box check confirmed it**.
   An unconfirmed cell never counts as a vote.
2. **Confident only when ≥2 voting sources all agree and no cell value disagrees** (confirmed or not, prefix or suffix
   relation or anything else). Any disagreement gives needs_gold, with the value kept as a suggestion. An unconfirmed cell can
   therefore never decide; it can only block.
3. **Cell-only GW** (no page/token source) is never accepted by the BL alone, and the widened-box confirmation is not enough. The BL
   row carries `meta.bl_gw_cell_only`. The batch step `corroborate_cell_only_gw` (run at the end of
   `dedupe_shared_packing_units`, so after shipment_first, in CLI/GUI) lifts the flag **only if the cell value equals the
   INV/PL G.W. total of all invoices on that waybill**:
   - the waybill is identified by the same BL file + BL No.;
   - one value per invoice no., so PDF/xlsx twins count once;
   - if any invoice lacks a G.W. or its twins disagree, there is no total and the flag stays.

Coverage of the review findings:
- **A (right cut):** unconfirmed 1.774 + one 1774.5 → needs_gold; 3.084 + 3084.5 → needs_gold. Any disagreeing cell blocks.
- **C:** token 4998 ×3 = one vote. Against a confirmed cell 1998 that is 1:1 → needs_gold.
- **D:** A = 774.5 + B = 1,000 (total 1,774.5) with a left-cut cell 774.5 → needs_gold. A cell of 1,774.5 equals the total and is accepted.
- **B:** a confirmed cell alone → needs_gold unless it equals the shipment total.

## Real scans (explicit, as asked)

| Scan | Sources | Cell | Result |
|---|---|---|---|
| 6th case 8 KEE602 (raw 3-page) | none | 50 (confirmed, cell only) | BL alone needs_gold; INV/PL total 50 (1 invoice) → **261002KEE602 / 1 / 50, pass** |
| 6th case 9 `WAYBILL.pdf` | clean 1,774.5, tok 1,774.5 | **774.5 unconfirmed** (box lost the leading `1,`, 11/12) | **CHANGED → BL G.W. needs_gold** (suggestion 1,774.5) |
| 6th case 10 Ocean Links | r1, clean, tok = 1,460.9 | none | 1,460.9, pass (unchanged) |
| BHC 4th case 8 `WAYBILL.pdf` | r1, clean, tok = 3,084.5 | 3,084.5 confirmed | 3,084.5, pass (unchanged) |
| BHC 4th case 6 `BL.pdf` | clean 1,998, tok 1,998 | no majority | 1,998, pass (unchanged) |

**6th case 9 becomes needs_gold.** This is the honest result under the conservative rule, not loosened:
- The page and token reads say 1,774.5, but the located cell reads 774.5 at 11 of 12.
- The scan prints **1,774.500 KGS** (= INV/PL 1,774.5; crop `crops/case9_bl_pkg_gw.png`). So the suggestion is right, but the reads disagree.
- Both twin rows (PDF and xlsx) now have `bl_gross_weight_kg` needs_gold with hard verdict needs_gold. Gold: 261002KEE101 / 6 / **1,774.5**.
- The cell box truncation comes from the box-intersection geometry. Fixing it would be another patch, so it is left for a decision.

## Other fixes

- **Note when exactly one waybill has exactly one matching read:** it now says `too few matching INVOICE NO. reads for … (1 read; ≥2 needed)` (before, it said "none matched").
- **Round-3 doc correction:** `auditor_round3.md` now states that BHC 2nd case 1 changed `meta.needs_gold` False → True on both rows (fix 2(b)), with values, fields and verdict unchanged. My harness does not record `meta.needs_gold`, which is why it was missed.
- **OCR timeout:** tesseract/pdftoppm subprocess timeouts went from 120/180 s to **600 s**, overridable with `INVOICE_OCR_TIMEOUT` (`ocr.OCR_TIMEOUT_S`, also used by `ocr_reread`). Under heavy load a scan page could time out and come back blank (6th case 10, round-3 note).

## Tests (`tests/test_bhc_6th.py`)

New or rewritten for round 4:
- `test_gw_true50_two_misread150_is_needs_gold` (confirmed and unconfirmed cell)
- `test_gw_single_misread150_vs_confirmed_50_is_needs_gold`
- `test_gw_right_cut_unconfirmed_cell_vs_one_page_read_is_needs_gold[1.774-1774.5]`, `[3.084-3084.5]`
- `test_gw_unconfirmed_cell_disagreeing_blocks[774.5-1774.5]`, `[84.5-3084.5]`, `[1.774-1774.5]`, `[3.084-3084.5]`
- `test_gw_token_rereads_are_one_source` (4998 ×3 vs confirmed 1998 → needs_gold)
- `test_gw_any_disagreement_between_sources_is_needs_gold`
- `test_gw_cell_only_is_never_decided_by_the_bl[False/True-774.5/1.774/50.0]` (6 cases)
- `test_cell_only_gw_corroborated_by_shipment_total_only`:
  - A 774.5 + B 1,000 with cell 774.5 → needs_gold;
  - a cell of 1,774.5 = total → accepted;
  - twins counted once;
  - a missing invoice GW keeps the flag;
  - a right-cut 1.774 stays flagged;
  - another waybill's rows are excluded.
- `test_select_note_single_matching_read_says_too_few`
- End-to-end:
  - `test_case8_original_3page_scan_end_to_end`: the row is flagged before the batch step, then 261002KEE602 / 1 / 50 pass after it.
  - `test_jif_real_scan_gw_with_cell_reread[4th case8 3,084.5]`, `[4th case6 1,998]`.
  - `test_case9_waybill_gw_needs_gold_when_cell_disagrees`.

The round-3 tests that encoded the old weighting were replaced: single 150 vs 50, the "majority wins" tail vote, and confirmed cell-only accepted.

## Verification

- **Full pytest:** 379 passed, 3 skipped (the skips are `test_pt_dremel` fixtures that are missing).
- **Regression BHC 2nd–5th + mega (32 folders):**
  - vs `main` @4fab308: Result fields differ only in BHC 3rd case 5. BHC 2nd case 1 `meta.needs_gold` False→True carries over from round 3; the harness doesn't record that field.
  - vs 6400611: **0 rows differ**.
- **BHC 6th vs 6400611:** **only case 9** differs. Both twin rows have BL G.W. 1,774.5 now flagged, verdict pass → needs_gold. Case 8 is unchanged (pass, now via the INV/PL total). The other 13 cases are identical.

## Output changes

- 6th case 9, rows `IV_117-BHCTW-26K-43.PDF` and `.xlsx`: `bl_gross_weight_kg` 1,774.5 is now **needs_gold** (verdict pass → needs_gold). This is the only change.
