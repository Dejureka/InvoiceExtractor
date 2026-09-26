# SOE 2nd batch — audit report (invoice-only scope) — Round 2

**Auditor Round 1 @7118522:** 13 pass, 2 conflict, 0 needs_gold (`out/soe_2nd_auditor_review.md`, crops `/workspace/soe2audit/`). Conflicts: 7369301 (160) and 7405713 (167) `items[0].part_no` `-576` → print `0265.011.097-57G`. 1267475174 (167): needs_gold was a false flag, so it is pass. 168 pkg=5 was confirmed (5 HUs; the booking image says 5 PALLETS; only the email subject says 10). 166 empty pkg was accepted. **Round 2** implements Auditor's PN reconciliation rule generically in `soe_rb_gmbh_v1`.

Branch `feature/soe-2nd` · input `/home/box/Downloads/SOE-batch-2nd/2nd data/` (12 .msg + 1 loose PDF) · attachments extracted to `/home/box/Downloads/SOE-batch-2nd/extracted/<case>/` (inline png/jpg/gif skipped).

**Scope change (user):** only invoices are run. HBL/BL PDFs, packing lists, the XC PL .xlsx and other non-invoices are skipped. Document type decided by content. No BL pairing, no new BL formats. Missing pkg/G.W. is not a failure when the invoice itself does not print it.

## Summary

- Invoices run: **15** (13 cases). Verdicts: **15 pass**, **0 needs_gold**, **0 conflict**.
- format_id: all `soe_rb_gmbh_v1` (**existing, extended**). No new format_id.
- HS strictness for SOE (checker, unchanged): `soe_rb_gmbh_v1` is in `REQUIRE_LINE_HS_FORMATS` (`src/invoice_extractor/checker.py`) → any line without HS = hard conflict (same as PT/MA; BHC is soft). Result: HS present on 17/17 lines.
- `meta.labeled_amount` (`Invoice amount`) is populated on all 15 and matches header.amount and sum(lines) on all 15.
- OCR: 4 scanned PDFs (cargo list + transport order + delivery note + invoice in one file) and 1 PDF whose body glyphs are vector outlines (thin text layer, 7077515945) go through Tesseract. Round 2: PN readings across item row / Customer PN / cargo list / transport order are reconciled. 7369301 and 7405713 now give `0265.011.097-57G`, 1267475174 stays `-57G`, and all three pass.

## Items for human / manual verification

No needs_gold and no conflict remain. Info / FYI only:

| File | Status | Note |
|---|---|---|
| 7369301.pdf (50-D-26SOE-160) | pass (info) | OCR PN reconciled 0265.011.097: readings -57G×2, -576×2 — -57G/-576 differ only by letter/digit look-alikes, letter form -57G kept (item row read -576). Auditor confirmed the print shows `0265.011.097-57G` |
| 1267475174 taiwan.pdf (50-D-26SOE-167) | pass (info) | OCR PN reconciled 0265.011.097: readings -576×2, -876×1, -57G×4 — -576/-57G differ only by letter/digit look-alikes, letter form -57G kept (outlier -876 ignored). Auditor confirmed the print shows `0265.011.097-57G` |
| 7405713.pdf (50-D-26SOE-167) | pass (info) | OCR PN reconciled 0265.011.097: readings -57G×1, -576×3 — -57G/-576 differ only by letter/digit look-alikes, letter form -57G kept (item row read -576). Auditor confirmed the print shows `0265.011.097-57G` |
| 7077515945.pdf (90-S-26SOE-166) | pass + soft | Page 3/3 (Marking/pallets) is not in the PDF, so pkg is empty (accepted by Auditor). **GW FYI:** the invoice prints Total gross weight 24.000 kg; the out-of-scope HBL WT20260814000087 and the XC PL xlsx say 27.000 kg / 1 pallet. If shipping GW is wanted it must come from PL/HBL (human decision) |
| 7077513531.pdf (90-S-26SOE-168) | pass | pkg 5 confirmed by Auditor (5 RB HUs × 480 PC = 2,400; booking image 5 PALLETS). The email subject '10 Pallets' is a subject discrepancy to raise with the shipper |
| 7077513532.pdf (90-S-26SOE-169) | pass | FYI (Auditor): the inline booking image in that email (Keelung / 5 PALLETS) does not match this KHH shipment. Reference only |

## Email pallet cross-check (reference only)

| Case | Email-stated | Invoice pkg | Match |
|---|---|---|---|
| 50-D-26SOE-160 (7369301.pdf) | — (not stated) | 2 | — |
| 50-D-26SOE-167 (1267475174 taiwan.pdf) | — (not stated) | 5 | — |
| 50-D-26SOE-167 (1267502206 taiwan.pdf) | — (not stated) | 1 | — |
| 50-D-26SOE-167 (7405713.pdf) | — (not stated) | 1 | — |
| 50-N-26SOE-165 (7077519466.pdf) | 1 pallet (body) | 1 | ✓ |
| 90-S-26SOE-162 (7077505806.pdf) | 3 Pallets (subject) | 3 | ✓ |
| 90-S-26SOE-163 (7077505805.pdf) | 2 Pallets (subject) | 2 | ✓ |
| 90-S-26SOE-166 (7077515945.pdf) | 1 pallet (body; 'refer to attached PL') | — | n/a (not printed) |
| 90-S-26SOE-168 (7077513531.pdf) | 10 Pallets (subject, 'Revised 1') | 5 | **✗ email subject only** (invoice + booking image say 5; Auditor: pkg 5 correct) |
| 90-S-26SOE-169 (7077513532.pdf) | 2 Pallets (subject) | 2 | ✓ |
| 90-S-26SOE-171 (7077520279.pdf) | 2 pallet (body) | 2 | ✓ |
| 90-S-26SOE-172 (90-S-26SOE-172_7077517937.PDF) | 1pallet (MPC 0203.502.743-2Y8, in 171/173 body) | 1 | ✓ |
| 90-S-26SOE-173 (7077518609.PDF) | 8 pallet (body) | 8 | ✓ |
| 90-S-26SOE-176 (7077524710.pdf) | 5>1 Pallet (subject, revised to 1) | 1 | ✓ |
| 90-S-26SOE-177 (7077523112.pdf) | 5 Pallets (subject) | 5 | ✓ |

## Review pack

- Screenshots: `docs/review_shots/soe_2nd/<case>__<file>-keyfields.png` (key-field panel + PDF crops: header, item rows, totals, G.W., Marking/pallets; for PN needs_gold, every OCR reading of the PN).
- JSON: `docs/review_shots/soe_2nd/<case>__<file>.json`, all-in-one `_auditor_payload_all15.json`.
- Excel (same template, not the root file): `out/soe_2nd/SOE2_invoices_Result.xlsx`. needs_gold shows in meta `checker_verdict`.
