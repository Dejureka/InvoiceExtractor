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

## Document inventory (by content)

| Case | File | Document type (by content) | Action |
|---|---|---|---|
| 50-D-26SOE-160 | 7369301.pdf | Scan: cargo list + transport order + delivery note 1267369301 + **Robert Bosch GmbH Invoice Copy 7091800640** (p4–5) | run (invoice pages) |
| 90-S-26SOE-162 | 7077505806.pdf | Robert Bosch GmbH Invoice Copy 7077505806 | run |
| 90-S-26SOE-163 | 7077505805.pdf | Robert Bosch GmbH Invoice Copy 7077505805 | run |
| 50-N-26SOE-165 | 7077519466.pdf | Robert Bosch GmbH Invoice Copy 7077519466 | run |
| 50-N-26SOE-165 | NCN93230104.pdf | Nippon Express (China) **air waybill / HAWB** NCN 9323 0104 (PVG–HKG–KHH, refs INV 7077519466) | **skipped** (AWB, not an invoice) |
| 90-S-26SOE-166 | 7077515945.pdf | Robert Bosch GmbH Invoice Copy 7077515945 (pages 1/3 and 2/3 only; body text is vector outlines) | run (OCR) |
| 90-S-26SOE-166 | WT20260814000087 HBL 上海盟联--KAOHSIUNG.pdf | House B/L (Shanghai Menglian Intl Logistics) | **skipped** (HBL) |
| 90-S-26SOE-166 | XC PL 25996773(8-14)SEA .xlsx | Packing list (Excel) | **skipped** (packing list) |
| 50-D-26SOE-167 | 7405713.pdf | Scan: cargo list + transport order + delivery note 1267405713 + **Invoice Copy 7091801079** | run (invoice pages) |
| 50-D-26SOE-167 | 1267475174 taiwan.pdf | Scan: cargo list + transport order + delivery note + **Invoice Copy 7091801544** (3 pages) | run (invoice pages) |
| 50-D-26SOE-167 | 1267502206 taiwan.pdf | Scan: cargo list + transport order + delivery note + **Invoice Copy 7091801668** | run (invoice pages) |
| 90-S-26SOE-168 | 7077513531.pdf | Robert Bosch GmbH Invoice Copy 7077513531 | run |
| 90-S-26SOE-169 | 7077513532.pdf | Robert Bosch GmbH Invoice Copy 7077513532 | run |
| 90-S-26SOE-171 | 7077520279.pdf | Robert Bosch GmbH Invoice Copy 7077520279 | run |
| 90-S-26SOE-171 | WT20260813000110 HBL 博世汽车部件(苏州)有限公司--TAICHUNG.pdf | House B/L | **skipped** (HBL) |
| 90-S-26SOE-172 | 90-S-26SOE-172_7077517937.PDF (loose) | Robert Bosch GmbH Invoice 7077517937 | run |
| 90-S-26SOE-173 | 7077518609.PDF | Robert Bosch GmbH Invoice 7077518609 | run |
| 90-S-26SOE-173 | WT20260804000230 HBL 博世汽车部件(苏州)有限公司--TAICHUNG.pdf | House B/L | **skipped** (HBL) |
| 90-S-26SOE-176 | 7077524710.pdf | Robert Bosch GmbH Invoice Copy 7077524710 | run |
| 90-S-26SOE-177 | 7077523112.pdf | Robert Bosch GmbH Invoice Copy 7077523112 | run |

Email bodies were used only as a cross-check reference, not as extraction input.

## Per invoice

| Case | File | format_id | Backend | Invoice No. | Date | Cur | Amount (= labeled) | Lines | Qty | Pkg | G.W. kg | Origin | HS | Part no. | Incoterm | Hard |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 50-D-26SOE-160 | 7369301.pdf | soe_rb_gmbh_v1 (extended) | ocr/tesseract | 7091800640 | 2026-08-06 | EUR | 21,852.90 (= 21,852.90) | 1 | 672 | 2 | 53.000 | ES | 90318080 | 0265.011.097-57G | FCA Guadalajara | **pass** |
| 50-D-26SOE-167 | 1267475174 taiwan.pdf | soe_rb_gmbh_v1 (extended) | ocr/tesseract | 7091801544 | 2026-08-20 | EUR | 72,843.01 (= 72,843.01) | 1 | 2240 | 5 | 160.000 | ES | 90318080 | 0265.011.097-57G | FCA Guadalajara | **pass** |
| 50-D-26SOE-167 | 1267502206 taiwan.pdf | soe_rb_gmbh_v1 (extended) | ocr/tesseract | 7091801668 | 2026-08-21 | EUR | 3,642.15 (= 3,642.15) | 1 | 112 | 1 | 16.000 | ES | 90318080 | 0265.011.097-57G | FCA Guadalajara | **pass** |
| 50-D-26SOE-167 | 7405713.pdf | soe_rb_gmbh_v1 (extended) | ocr/tesseract | 7091801079 | 2026-08-13 | EUR | 3,642.15 (= 3,642.15) | 1 | 112 | 1 | 16.000 | ES | 90318080 | 0265.011.097-57G | FCA Guadalajara | **pass** |
| 50-N-26SOE-165 | 7077519466.pdf | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077519466 | 2026-08-21 | EUR | 11,759.18 (= 11,759.18) | 1 | 1440 | 1 | 220.500 | CN | 90303370 | 0199.300.151-1HX | FCA Bosch Plant | **pass** |
| 90-S-26SOE-162 | 7077505806.pdf | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077505806 | 2026-08-10 | EUR | 76,788.72 (= 76,788.72) | 1 | 1440 | 3 | 1,002.516 | TH | 90328100 | 0265.299.799-5R9 | FCA DISPATCH POINT | **pass** |
| 90-S-26SOE-163 | 7077505805.pdf | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077505805 | 2026-08-10 | EUR | 49,902.72 (= 49,902.72) | 1 | 960 | 2 | 668.344 | TH | 90328100 | 0265.299.986-5R9 | FCA DISPATCH POINT | **pass** |
| 90-S-26SOE-166 | 7077515945.pdf | soe_rb_gmbh_v1 (extended) | ocr/tesseract+thin_text_layer | 7077515945 | 2026-08-19 | EUR | 2,834.18 (= 2,834.18) | 3 | 892 | — | 24.000 | DE, CN | 8708999900 | 0263.036.668-2U1, 0263.036.669-2U1, 0215.000.838-2U1 | FCA DISPATCH POINT | **pass** |
| 90-S-26SOE-168 | 7077513531.pdf | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077513531 | 2026-08-17 | EUR | 124,756.80 (= 124,756.80) | 1 | 2400 | 5 | 1,526.110 | TH | 90328100 | 0265.298.014-5R9 | FCA DISPATCH POINT | **pass** |
| 90-S-26SOE-169 | 7077513532.pdf | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077513532 | 2026-08-17 | EUR | 51,192.48 (= 51,192.48) | 1 | 960 | 2 | 668.344 | TH | 90328100 | 0265.299.799-5R9 | FCA DISPATCH POINT | **pass** |
| 90-S-26SOE-171 | 7077520279.pdf | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077520279 | 2026-08-21 | EUR | 37,174.27 (= 37,174.27) | 1 | 3840 | 2 | 213.000 | CN | 90318080 | 0265.019.150-2CG | FCA Suzhou | **pass** |
| 90-S-26SOE-172 | 90-S-26SOE-172_7077517937.PDF | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077517937 | 2026-08-20 | EUR | 83,636.63 (= 83,636.63) | 1 | 750 | 1 | 214.500 | CN | 85371091 | 0203.502.743-2Y8 | FCA Changzhou | **pass** |
| 90-S-26SOE-173 | 7077518609.PDF | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077518609 | 2026-08-20 | EUR | 134,872.32 (= 134,872.32) | 1 | 1536 | 8 | 3,544.000 | CN | 90328100 | 0265.298.800-2CG | FCA Suzhou | **pass** |
| 90-S-26SOE-176 | 7077524710.pdf | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077524710 | 2026-08-25 | EUR | 28,938.62 (= 28,938.62) | 1 | 480 | 1 | 303.308 | TH | 90328100 | 0265.311.369-5R9 | FCA DISPATCH POINT | **pass** |
| 90-S-26SOE-177 | 7077523112.pdf | soe_rb_gmbh_v1 (extended) | pdftotext -layout | 7077523112 | 2026-08-24 | EUR | 30,205.60 (= 30,205.60) | 1 | 8000 | 5 | 547.100 | TH | 90318080 | 0265.008.770-5R9 | FCA DISPATCH POINT | **pass** |

## soe_rb_gmbh_v1 extensions (additive, v1 meaning unchanged)

1. **OCR PN separator repair.** OCR splits the Bosch PN (`0263 .036.668-2U1`, `0265.011, 097-576`); the separators are normalised.
2. **OCR PN reconciliation (OCR only; Round 2, Auditor rule).** Collect every reading of the 10-digit PN stem in the scan: invoice item row (dotted Bosch PN), Customer PN column (no-dot form, e.g. `026501109757G`), and cargo list / transport order / delivery note PN fields. A reading only counts when the full stem directly precedes the 3-char suffix, and lines whose text before the PN is a numeric label (Volume/cdm/weight/kg/Sum) are skipped. So `26) Volume in cdm 576` can never be a candidate. Readings that differ only by letter/digit look-alikes (G/6, S/5, B/8, O/0, Z/2, I/1) form one class. If that class is a strict majority, the **letter form** is used and outliers are ignored, with an info note in `meta.notes`. Otherwise `items.part_no` becomes needs_gold. A separator misread with no second reading to confirm it also gives needs_gold. Text-layer PDFs are never touched.
   - Why the letter form and not 'Customer PN first': on 7369301 and 7405713 Tesseract also reads the printed Customer PN `026501109757G` as `0265011097576`. Targeted re-OCR of that crop at 300/400/600 dpi still gives `…576`. So the OCR'd Customer PN can't break the tie. What is reliable is the direction of the error: Tesseract reads this font's G as 6, never 6 as G. Letter suffixes are normal in this series (-5R9, -2CG, -1HX, -2U1, -2Y8).
   - Pipeline candidates (from the OCR text): 7369301 -57G×2 (p2 transport order), -576×2 (p4 item row Bosch + Customer PN). 7405713 -57G×1, -576×3. 1267475174 -57G×4, -576×2, -876×1 (outlier). 1267502206 -57G only.
3. **G.W. fallback:** when there is no `Total gross weight` line, use the Marking summary `N Pallets / Net weight … Gross weight : X KG` (7077520279 → 213.000). `Total gross weight` still wins when printed (test).
4. **Origin fallback:** a bare country line (e.g. `CN`, no per-line Net weight) above `Customs tariff no` (7077520279).
5. **pkg:** typed Marking summary `: 5 cardboard pallet` (OCR may read `pailet`) is used before cargo-list fallbacks (1267475174).
6. **Soft note:** when printed page marks `k / M` show a page missing from the PDF (7077515945 has only 1/3 and 2/3, so the Marking/pallet page is absent and pkg stays empty).
7. OCR label tolerance: `Date Invoice + 06.08.2026`, `Invoice amount =: EUR`.
8. **rules_engine (generic, retry only):** if a PDF text layer is *thin* (<400 non-space chars/page, ≤10 pages) **and no format matched**, OCR once and re-classify (backend `ocr/tesseract+thin_text_layer`). PDFs that already classify never reach this path (test). A scan of the other 181 PDFs under ~/Downloads found only 9 thin, unclassified PDFs, all MA `Label_*.pdf` (24–138 pages). They are excluded by the page cap and stay unmatched either way.

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
