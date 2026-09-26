# SOE 2nd batch — audit report (invoice-only scope)

Branch `feature/soe-2nd` · input `/home/box/Downloads/SOE-batch-2nd/2nd data/` (12 .msg + 1 loose PDF) · attachments extracted to `/home/box/Downloads/SOE-batch-2nd/extracted/<case>/` (inline png/jpg/gif skipped).

**Scope change (user):** only invoices are run. HBL/BL PDFs, packing lists, the XC PL .xlsx and other non-invoices are skipped. Document type decided by content. No BL pairing, no new BL formats. Missing pkg/G.W. is not a failure when the invoice itself does not print it.

## Summary

- Invoices run: **15** (13 cases). Verdicts: **12 pass**, **3 needs_gold**, **0 conflict**.
- format_id: all `soe_rb_gmbh_v1` (**existing, extended**). No new format_id.
- HS strictness for SOE (checker, unchanged): `soe_rb_gmbh_v1` is in `REQUIRE_LINE_HS_FORMATS` (`src/invoice_extractor/checker.py`) → any line without HS = hard conflict (same as PT/MA; BHC is soft). Result: HS present on 17/17 lines.
- `meta.labeled_amount` (`Invoice amount`) is populated on all 15 and matches header.amount and sum(lines) on all 15.
- OCR: 4 scanned PDFs (cargo list + transport order + delivery note + invoice in one file) and 1 PDF whose body glyphs are vector outlines (thin text layer, 7077515945) go through Tesseract. 3 of the scans are needs_gold on `items.part_no` only (OCR reads the PN suffix as 57G in some places and 576 in others). All other hard checks on them pass.

## Items for human / manual verification

| File | Status | Reason |
|---|---|---|
| 7369301.pdf (50-D-26SOE-160) | needs_gold `items.part_no` | OCR misread part no. separators (0265.011, 097-576) / OCR readings of the same part no. disagree in this scan (line 01 0265.011.097-576: suffix readings -57G×2, -576×2). Kept value `0265.011.097-576`; the image and the email show **0265.011.097-57G** |
| 1267475174 taiwan.pdf (50-D-26SOE-167) | needs_gold `items.part_no` | OCR readings of the same part no. disagree in this scan (line 01 0265.011.097-57G: suffix readings -576×2, -876×1, -57G×4). Kept value `0265.011.097-57G`; the image and the email show **0265.011.097-57G** |
| 7405713.pdf (50-D-26SOE-167) | needs_gold `items.part_no` | OCR readings of the same part no. disagree in this scan (line 01 0265.011.097-576: suffix readings -57G×1, -576×3). Kept value `0265.011.097-576`; the image and the email show **0265.011.097-57G** |
| 7077515945.pdf (90-S-26SOE-166) | pass + soft | Page 3/3 (Marking/pallets) is not in the PDF, so pkg is empty (allowed: the invoice pages provided do not print it). Email says 1 pallet. The skipped XC PL xlsx (FYI only) says 1 pallet, GW 27 kg, vs invoice Total gross weight 24.000 kg |
| 7077513531.pdf (90-S-26SOE-168) | pass | Email subject says **10 Pallets** ('Revised 1'), but the invoice prints 5 RB pallet blocks + `5 Pallets` summary and GW 1,526.110. The tool keeps 5 (as printed) |
| 7369301.pdf / 7405713.pdf / 1267475174 / 1267502206 | info | Scans bundle cargo list, transport order and delivery note with the invoice. Values are taken from the invoice pages (Marking pallets, Total gross weight) |

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
| 90-S-26SOE-168 (7077513531.pdf) | 10 Pallets (subject, 'Revised 1') | 5 | **✗ mismatch** |
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
