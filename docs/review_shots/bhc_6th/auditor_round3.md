# BHC 6th — Auditor round 3 (2026-10-08)

The Auditor's round-2 review @adfd279 (`out/bhc_6th_round2_auditor_review.md`) found all 15 outputs correct.
Item 3, the GW cell re-read guard, had to be fixed before close. This round fixes it and also takes the
three nice-to-fix notes from item 2. Branch `feature/bhc-6th`, not pushed and not merged.

## Must fix (item 3)

### Risk 1: the "tail of another read" guard dropped the cell
- **Before:** if any single page or token read ended with the cell value's digits, the cell value was dropped. Example: true 50 with a hatch misread of 150 ×2 gave a confident 150.
- **Now** (`jif_cosmo_waybill_v1._decide_gw`): the cell always stays in the GW vote as 2 reads. The vote needs ≥2 agreeing reads and a strict majority, otherwise GW is needs_gold.
- **Leading-digit differences** (`84.5`/`3,084.5`, `50`/`150`) are written in the notes and no longer remove the cell.
- **Extra safety:** an *unconfirmed* cell value that is the tail of a longer read cannot win the vote. Example: 3,084.5 ×1 against a truncated cell 84.5 ×2 is needs_gold, not 84.5.

| Scenario | Result |
|---|---|
| true 50: page 150 ×2 + cell 50 (2 reads) | 2:2 tie → **needs_gold** |
| page 150 ×1 + confirmed cell 50 | **50**, confident |
| page 150 ×1 + unconfirmed cell 50 | needs_gold |
| 6th case 9: page/token 1,774.5 ×4 + cell 774.5 | **1,774.5**, confident (cell outvoted, noted) |
| BHC 4th case 8: page/token 3,084.5 ×5 + cell 3,084.5 | **3,084.5**, confident |
| page 3,084.5 ×1 + unconfirmed cell 84.5 | needs_gold |

### Risk 2: GW from the cell alone must be corroborated
When the page and token passes have no GW read, the cell value is accepted only in one of two cases:
1. **Whole number confirmed.** The cell box is widened to the column limits (1.5 h left, up to 2.5 h right, capped at
   header x1 + 1 h) and re-read 12× with the same integer/decimal vote. The widened result must equal the cell value. A box that lost the
   leading `1,` or the decimals reads differently once widened. Example: case 9's box reads 774.5 but the widened box reads 1,774.5, so it is not confirmed.
2. **Equal to the paired INV/PL G.W.** The BL keeps the value as a suggestion with needs_gold and sets
   `meta.gw_cell_unverified`. `pairing.corroborate_cell_gw` lifts the flag only if the paired invoice/PL G.W. is
   equal (±0.005), and notes it.

Otherwise GW stays needs_gold. A left-truncated `774.5` or a right-truncated `1.774` against INV/PL 1,774.5 stays needs_gold.
This also covers risk 3 (`5,000` → 5.0), which comes from the same cause.

Real scans (`extract_bl`, after the fix):

| file | page/token GW reads | cell | widened box | output |
|---|---|---|---|---|
| 6th case 8 p3 (KEE602) | none | 50 (8/12) | 50 → **confirmed** | 261002KEE602 / 1 / **50** (would also pass via INV/PL 50) |
| 6th case 8 p1 (KEE601, not output) | none | 745 (8/12) | no majority → not confirmed | 745 + needs_gold inside `documents` |
| 6th case 9 `WAYBILL.pdf` | 1,774.5 ×4 | 774.5 (11/12, truncated) | 1,774.5 → not confirmed | **1,774.5** (majority; tail noted) |
| 6th case 9 scan copy | none | no cell value | – | needs_gold pkg+GW (as before; duplicate copy, not used) |
| BHC 4th case 8 `WAYBILL.pdf` | 3,084.5 ×5 | 3,084.5 (9/12) | 3,084.5 → confirmed | **3,084.5** |
| BHC 4th case 8 scan copy | none | no cell value | – | needs_gold (as before; not used) |
| BHC 4th case 6 `BL.pdf` | 1,998 ×4 | no majority | – | **1,998** |

## Nice-to-fix (item 2)

- **(a) Note text:** when more than one waybill matches, the note now says `printed INVOICE NO. … matched more than one waybill (N)`. The other no-selection cases say `none has a printed INVOICE NO. matching …` or `too few matching INVOICE NO. reads`.
- **(b) Row flag:** when `merge_bl_onto_inv` adds BL needs_gold fields, the row's `meta.needs_gold` is now True. Multi-waybill BL meta already set it.
- **(c) Exact match:** the invoice-no. match is now exact after look-alike folding. The "+≤2 trailing chars" tolerance is gone, so invoice `A1234` no longer selects a waybill printing `A12345`. Folding still applies, e.g. `A1Z345` = `A12345`.

## Tests (added to `tests/test_bhc_6th.py`)

- `test_gw_true50_two_misread150_is_needs_gold`
- `test_gw_single_misread150_does_not_knock_out_50`
- `test_gw_truncated_cell_still_votes_and_majority_wins[1774.5-774.5]` and `[3084.5-84.5]`: also checks that one page read against an unconfirmed truncated cell is needs_gold
- `test_gw_cell_only_truncated_needs_gold[774.5]` (left cut) and `[1.774]` (right cut)
- `test_gw_cell_only_confirmed_whole_number_accepted`
- `test_corroborate_cell_only_gw_with_inv_pl_gw`: 50 = 50 is lifted; 774.5 / 1.774 against 1,774.5 stay flagged; no INV GW stays flagged
- `test_select_requires_exact_invoice_no_after_folding`
- `test_select_note_when_more_than_one_waybill_matches`
- `test_merge_sets_row_needs_gold_when_bl_fields_flagged`
- End-to-end on the real scans: `test_jif_real_scan_gw_with_cell_reread[case9 WAYBILL.pdf 1,774.5]`, `[BHC 4th case8 WAYBILL.pdf 3,084.5]`,
  and the existing `test_case8_original_3page_scan_end_to_end` (261002KEE602 / 1 / 50). These skip when the scan is absent.

## Verification

- **Full pytest:** 368 passed, 3 skipped.
- **Regression BHC 2nd–5th + mega (32 folders) vs `main` @4fab308:** only BHC 3rd case 5 differs (the known round-1 Dunan pairing; audited gold). Same as round 2.
- **BHC 6th vs adfd279 (round-2 run):** 0 Result-field differences across all 15 cases (header, lines, BL fields, flags, verdict). Row notes are also identical.
- **Review-pack JSONs:** regenerated. The BL JSONs gained `meta.gw_cell_unverified` and the widened-box notes; 0 of the 37 pack JSONs differ from adfd279 in Result fields or flags.

## Output changes

None. All 15 BHC 6th Result rows and all 32 regression folders are unchanged vs round 2.
