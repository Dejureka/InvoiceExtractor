# BHC 6th — Auditor round 5 (2026-10-08)

The round-4 review @8a1cfcd (`out/bhc_6th_round4_auditor_review.md`) passed the new GW rule, with one must-fix.
Branch `feature/bhc-6th`, not pushed and not merged.

## Changes
1. **Must-fix:** in `pairing.corroborate_cell_only_gw`, an invoice row on the waybill **without an invoice no.** used to be skipped. It now blocks the total, the same as a missing G.W. There is no corroboration and the row stays needs_gold, with the note "total (n/a)".
2. **Row notes:** the BL note in the row notes is clipped at a `; ` item boundary (`pairing._clip_note`, limit 240, ending `…`). It is never cut mid-item, so no more `…not used: )`.
3. **`INVOICE_OCR_TIMEOUT`:** empty, non-numeric or ≤0 values now fall back to the 600 s default (`ocr._timeout_from_env`). Before, a bad value raised ValueError at import.
4. **SOP:** residual risks are documented, with no code change:
   - the de-hatched page and the token re-read come from one image and can be wrong together;
   - in partial-invoice runs, a cut cell value can equal a partial sum;
   - `tvl_hbl_v1` is not yet on one-vote-per-source (its 3 token DPIs = 3 votes).

   The user's decision is also recorded: 6th case 9 (1,774.5) and 2nd case 1 `QDEX2609010.jpg` stay needs_gold, with no hardcoded values.

## Tests (`tests/test_bhc_6th.py`)
- `test_cell_only_gw_missing_invoice_no_blocks_total`: A = 774.5, B = 1,000 with B's invoice no. unread and cell 774.5 → needs_gold. A cell equal to the readable invoice's G.W. is not accepted either.
- `test_bl_note_clipped_at_item_boundary`
- `test_ocr_timeout_env_fallback[...]` (8 values: `abc`, empty, None, `-5`, `0`, `900`, ` 45 `, `120.0`)
- `test_ocr_module_imports_with_bad_timeout_env` (import in a subprocess with `INVOICE_OCR_TIMEOUT=not-a-number` → 600)

## Verification
- Full pytest: **390 passed, 3 skipped** (`test_pt_dremel` fixtures missing, as before).
- Quick regression vs 8a1cfcd (BHC 6th, 15 folders; BHC 2nd–5th + mega, 32 folders): **no Result-field, `needs_gold_fields` or verdict changes.**
  - The only differences are in `notes`, on the rows whose BL note used to be cut mid-item: 6th case 8, 6th case 9 (2 rows) and 2nd case 1 (2 rows). These rows now show the complete items, e.g. case 8 `…not used: 261002KEE601 (pages [1, 2]) …` and case 9 `GW reads: clean=1774.5, tok=1774.5 (cell 774.5 unconfirmed, not voting) …`.
  - I updated the three affected review-pack JSONs (case 8, case 9 PDF and case 9 xlsx).
- Case 8 is still `261002KEE602 / 1 / 50`. Case 9 BL G.W. and 2nd case 1 stay needs_gold, as decided.
